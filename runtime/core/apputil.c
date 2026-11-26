/* Vita system calls on the host: SceAppUtil and common dialogs: save data and the save-data dialog (the
 * overlay draws its list and questions), dialogs that finish at once, trophies; system parameters, app
 * events, power, the console id, and the movie player (which refuses every movie). */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include "guestwatch.h"
#include "hle.h"
#include "ime.h"
#include "net.h"
#include "overlay.h"   /* (overlay_toast_titled: the network check's notice) */
#include "platform.h"
#include "player_paths.h"
#include "savedlg.h"
#include "settings.h"

/* ---- common dialogs: one that was opened finishes at once with an OK result, as if the player
 * confirmed it; each kind has its own state (a dialog never opened reports NONE). The save-data
 * dialog is the exception: a real one, below. */
enum { DLG_TROPHY, DLG_NETCHECK, DLG_MSG, DLG_EULA, DLG_N };
static int dialog_open[DLG_N];
#define DIALOG(kind, name) \
	static void h_##name##_init(Cpu *c) { dialog_open[kind] = 1; RET(0); } \
	static void h_##name##_status(Cpu *c) { RET(dialog_open[kind] ? 2 : 0); } /* FINISHED : NONE */ \
	static void h_##name##_term(Cpu *c) { dialog_open[kind] = 0; RET(0); }
DIALOG(DLG_TROPHY, trophy_dlg)
DIALOG(DLG_NETCHECK, net_dlg)
DIALOG(DLG_MSG, msg_dlg)
DIALOG(DLG_EULA, eula_dlg)
static void h_dialog_result(Cpu *c) { if (A0) WR32(A0, 0); RET(0); }
/* SceNetCheckDialogResult {result, psnModeSucceeded, ...}: online (net.h), connected and, in the PSN modes, signed in (np.c's
 * local account) -- with psnModeSucceeded left 0 Killzone took its Multiplayer connect as a failed sign-in and went quietly
 * back to the menu */
static void h_net_dlg_result(Cpu *c) {
	if (A0) { WR32(A0, 0); WR32(A0 + 4, net_online() ? 1 : 0); }
	if (!net_online() && net_online_needs()) {   /* the game went for its online modes on a version they aren't for: say why it can't (net.h) */
		static double told; const double now = (double)time(0);
		if (now - told > 20) { told = now; char b[200]; snprintf(b, sizeof b, "This copy of the game isn't the version online play is for. Add update %s in the launcher, then play again.", net_online_needs());
			char t[64]; snprintf(t, sizeof t, "Online play needs update %s", net_online_needs()); overlay_toast_titled(t, b, 10); }
	}
	RET(0);
}
/* Common dialog 0x12, which no NID list names (Init 33626E2C, Term BEBAEF25, Abort B55CF0E3, GetStatus B7D4C911, GetResult
 * D1858A78 in libcdlg, between the Facebook and cross-controller dialogs; SDK 2.10+). Read from the firmware and Killzone: the param
 * after the common one is a SceNpCommunicationId (+0x50) and a 32-bit version the game keeps in its profile (+0x5c), the 0x2c-byte
 * result {result, kind, version}. Killzone opens it after the network check on the way into Multiplayer and stores the version
 * of kind 1, clears it on kind 0, fails on 3 and goes on unchanged on 2 -- PSN's terms of service, as the PS3's sceNpEula checks
 * did. Answered "nothing new to accept" (kind 2): there is no PSN to show terms for. */
static void h_eula_dlg_result(Cpu *c) { if (A0) { for (int i = 0; i < 0x2c; i += 4) WR32(A0 + i, 0); WR32(A0 + 4, 2); } RET(0); }
static void h_zero(Cpu *c) { RET(0); }

/* The firmware dialog passes startup arguments through
 * SceSysmoduleOpt. These entries resolve only in the isolated firmware probe. */
enum { FW_MODULE_IDLE, FW_MODULE_STARTING, FW_MODULE_STARTED };
typedef struct {
	uint32_t id;
	const char *start_export;
	const char *stop_export;
	int state;
} DialogFirmwareModule;
static DialogFirmwareModule dialog_firmware[] = {
	{0x80000008u, "__recomp_start_libpaf", "__recomp_stop_libpaf", FW_MODULE_IDLE},
	{0x8000000cu, "__recomp_start_common_gui_dialog", "__recomp_stop_common_gui_dialog", FW_MODULE_IDLE},
	{0x80000012u, "__recomp_start_libcdlg_main", "__recomp_stop_libcdlg_main", FW_MODULE_IDLE},
	{0x80000015u, "__recomp_start_libcdlg_savedata", "__recomp_stop_libcdlg_savedata", FW_MODULE_IDLE},
};
static pthread_mutex_t dialog_firmware_lock = PTHREAD_MUTEX_INITIALIZER;
extern uint32_t module_export_addr(const char *name);

static DialogFirmwareModule *dialog_firmware_module(uint32_t id) {
	for (size_t i = 0; i < sizeof dialog_firmware / sizeof *dialog_firmware; i++)
		if (id == dialog_firmware[i].id) return &dialog_firmware[i];
	return NULL;
}

static void h_sysmodule_internal_status(Cpu *c) {
	DialogFirmwareModule *module = dialog_firmware_module(A0);
	pthread_mutex_lock(&dialog_firmware_lock);
	int loaded = module && module->state == FW_MODULE_STARTED;
	pthread_mutex_unlock(&dialog_firmware_lock);
	RET(loaded ? 0 : 0x805a1001u);
}

static void h_sysmodule_load_with_arg(Cpu *c) {
	DialogFirmwareModule *module = dialog_firmware_module(A0);
	uint32_t start = module ? module_export_addr(module->start_export) : 0;
	if (!start || (A1 && !A2) || !A3) {
		fprintf(stderr, "    firmware module %#x load unavailable (args %u)\n", A0, A1);
		RET(0x805a1000u);
		return;
	}
	uint32_t result_ptr = RD32(A3 + 4);
	if (!result_ptr) { RET(0x805a1000u); return; }

	pthread_mutex_lock(&dialog_firmware_lock);
	int state = module->state;
	if (state == FW_MODULE_IDLE) module->state = FW_MODULE_STARTING;
	pthread_mutex_unlock(&dialog_firmware_lock);
	if (state == FW_MODULE_STARTING) { RET(0x805a10ffu); return; }
	if (state == FW_MODULE_STARTED) { WR32(result_ptr, 0); RET(0); return; }

	fprintf(stderr, "    starting firmware module %#x (args %u)\n", A0, A1);
	uint32_t result = guest_call(c, start, A1, A2);
	pthread_mutex_lock(&dialog_firmware_lock);
	module->state = (int32_t)result < 0 ? FW_MODULE_IDLE : FW_MODULE_STARTED;
	pthread_mutex_unlock(&dialog_firmware_lock);
	WR32(result_ptr, result);
	fprintf(stderr, "    firmware module %#x start returned %#x\n", module->id, result);
	RET(0);
}

static void h_sysmodule_unload_with_arg(Cpu *c) {
	DialogFirmwareModule *module = dialog_firmware_module(A0);
	uint32_t stop = module ? module_export_addr(module->stop_export) : 0;
	if (!stop || (A1 && !A2) || !A3) { RET(0x805a1000u); return; }

	pthread_mutex_lock(&dialog_firmware_lock);
	int state = module->state;
	if (state == FW_MODULE_STARTED) module->state = FW_MODULE_STARTING;
	pthread_mutex_unlock(&dialog_firmware_lock);
	if (state != FW_MODULE_STARTED) { RET(0x805a1001u); return; }

	uint32_t status = RD32(A3 + 4);
	uint32_t result = guest_call(c, stop, A1, A2);
	pthread_mutex_lock(&dialog_firmware_lock);
	module->state = (int32_t)result < 0 ? FW_MODULE_STARTED : FW_MODULE_IDLE;
	pthread_mutex_unlock(&dialog_firmware_lock);
	if (status) WR32(status, result);
	fprintf(stderr, "    firmware module %#x stop returned %#x\n", module->id, result);
	RET(0);
}

/* A mounted vs0 already has a Vita path in this runtime. */
static void h_convert_vs0_path(Cpu *c) {
	if (!A0 || !A1 || !A2) { RET(0x80010016u); return; }
	const char *path = (const char *)G(A0);
	if (strncmp(path, "vs0:", 4)) { RET(0x80010016u); return; }
	size_t limit = A2 < 1024 ? A2 : 1024;
	size_t size = strnlen(path, limit);
	if (size == limit) { RET(0x8001005bu); return; }
	memmove(G(A1), path, size + 1);
	RET(0);
}

static void h_dialog_display_resolution(Cpu *c) {
	if (!A0 || !A1) { RET(0x80010016u); return; }
	WR32(A0, 960);
	WR32(A1, 544);
	RET(0);
}

/* PAF opens the save plug-in by path, then passes its plug-in
 * interface pointer to module_start. The image has already been mapped. */
#define FW_SAVE_MODULE_UID 0x62000015u
static void h_load_dialog_plugin(Cpu *c) {
	const char *path = A0 ? (const char *)G(A0) : "";
	if ((strcmp(path, "vs0:sys/external/libcdlg_savedata.suprx") &&
	     strcmp(path, "vs0:/sys/external/libcdlg_savedata.suprx")) ||
	    !module_export_addr("__recomp_start_libcdlg_savedata")) {
		fprintf(stderr, "    firmware plug-in not available: %.256s\n", path);
		RET(0x80010002u);
		return;
	}
	fprintf(stderr, "    mapped firmware plug-in %s\n", path);
	RET(FW_SAVE_MODULE_UID);
}

static void h_start_dialog_plugin(Cpu *c) {
	uint32_t start = module_export_addr("__recomp_start_libcdlg_savedata");
	if (A0 != FW_SAVE_MODULE_UID || !start || A1 != sizeof(uint32_t) || !A2) {
		RET(0x80010016u);
		return;
	}
	uint32_t status = STK(1);
	uint32_t result = guest_call(c, start, A1, A2);
	if (status) WR32(status, result);
	fprintf(stderr, "    firmware save plug-in start returned %#x\n", result);
	RET(FW_SAVE_MODULE_UID);
}

static void h_stop_dialog_plugin(Cpu *c) {
	uint32_t stop = module_export_addr("__recomp_stop_libcdlg_savedata");
	if (A0 != FW_SAVE_MODULE_UID || !stop || (A1 && !A2)) {
		RET(0x80010016u);
		return;
	}
	uint32_t status = STK(1);
	uint32_t result = guest_call(c, stop, A1, A2);
	if (status) WR32(status, result);
	RET(FW_SAVE_MODULE_UID);
}

static void h_unload_dialog_plugin(Cpu *c) { RET(A0 == FW_SAVE_MODULE_UID ? 0 : 0x80010016u); }

/* The isolated firmware images and resources are Vita 3.74. */
static void h_firmware_sdk_version(Cpu *c) { RET(0x03740000u); }
/* The firmware reads the configured UI language and confirm button. */
static void h_firmware_system_param(Cpu *c) {
	extern const char *host_lang(void);
	if (!A1 || (A0 != 0x00037502u && A0 != 0x00229142u)) { RET(0x800d0004u); return; }
	if (A0 == 0x00037502u) WR32(A1, !strcmp(host_lang(), "en") ? 1 : 0);
	else WR32(A1, 1);   /* Cross, matching the runtime's AppUtil system setting. */
	RET(0);
}
static void h_firmware_slot_param(Cpu *c);
static void h_firmware_slot_file_open(Cpu *c);
static void h_firmware_slot_file_get_param(Cpu *c);
static void h_firmware_slot_file_close(Cpu *c);

HleFn dialog_firmware_import(const char *name) {
	static const HleEntry imports[] = {
		{"sceSysmoduleLoadModuleInternalWithArg", h_sysmodule_load_with_arg},
		{"sceSysmoduleUnloadModuleInternalWithArg", h_sysmodule_unload_with_arg},
		{"sceSysmoduleIsLoadedInternal", h_sysmodule_internal_status},
		{"sceAppMgrConvertVs0UserDrivePath", h_convert_vs0_path},
		{"sceDisplayGetMaximumFrameBufResolution", h_dialog_display_resolution},
		{"sceKernelLoadModule", h_load_dialog_plugin},
		{"sceKernelStartModule", h_start_dialog_plugin},
		{"sceKernelStopModule", h_stop_dialog_plugin},
		{"sceKernelUnloadModule", h_unload_dialog_plugin},
		{"sceKernelGetAllowedSdkVersionOnSystem", h_firmware_sdk_version},
		{"sceRegMgrSystemParamGetInt", h_firmware_system_param},
		{"sceRegMgrUtilityGetInt", h_firmware_system_param},
		{"sceAppMgrSaveDataSlotGetParam", h_firmware_slot_param},
		{"sceAppMgrSaveDataSlotFileOpen", h_firmware_slot_file_open},
		{"sceAppMgrSaveDataSlotFileGetParam", h_firmware_slot_file_get_param},
		{"sceAppMgrSaveDataSlotFileClose", h_firmware_slot_file_close},
	};
	for (size_t i = 0; i < sizeof imports / sizeof *imports; i++)
		if (!strcmp(name, imports[i].name) && module_export_addr("__recomp_start_libcdlg_main"))
			return imports[i].fn;
	return 0;
}
static void h_drm_open(Cpu *c) {   /* every add-on licensed; RECOMP_NP_LOG names the ones the game asks for (Killzone's Botzone: P000000000001957) */
	static int log = -1; if (log < 0) log = getenv("RECOMP_NP_LOG") != 0;
	if (log && A0) { char id[18]; memcpy(id, G(A0), 17); id[17] = 0; fprintf(stderr, "    np: add-on licence %s -> licensed\n", id); }
	RET(0);
}
static void h_is_game(Cpu *c) { RET(1); }

/* ---- save data (SceAppUtil): savedata0: is <RECOMP_FS>/savedata0/. A slot exists once created or
 * saved: a file .slot<N> there holding its SceAppUtilSaveDataSlotParam, 0x34c bytes -- status +0,
 * title +0x4 (64 bytes), subTitle +0x44 (128), detail +0xc4 (512), iconPath +0x2c4, userParam +0x304,
 * sizeKB +0x308, modifiedTime +0x30c (SceDateTime: u16 year, month, day, hour, minute, second; u32
 * us). The texts are UTF-8 -- vitasdk's apputil.h declares them SceWChar16, but Uncharted writes
 * "Uncharted: Golden Abyss\u2122" / its chapter / "Difficulty: Normal..." as UTF-8 (2026-10-10).
 * The console stamps the modified time at every write; the host stamps its local clock. A marker
 * from before 2026-10-10 is empty: a slot with a blank param (the list dates it by the file). */
#define SLOT_PARAM_SIZE 0x34c
static void slot_marker(uint32_t id, char *buf, size_t n) { snprintf(buf, n, "%s/savedata0/.slot%u", player_save_root(), id); }
static int slot_read(uint32_t id, uint8_t *p) {   /* the slot's param into p (zeros past what the file holds); 0: no such slot */
	char m[1024]; slot_marker(id, m, sizeof m);
	memset(p, 0, SLOT_PARAM_SIZE);
	FILE *f = fopen(m, "rb"); if (!f) return 0;
	if (fread(p, 1, SLOT_PARAM_SIZE, f)) {}
	fclose(f); return 1;
}

/* The 3.74 savedata plug-in opens a slot-file snapshot into a 0x228-byte
 * buffer and indexes its signed existence bytes at +0x28 by slot ID. Its
 * GetParam then asks for the 0x400-byte record by ID, whose first 0x34c bytes
 * are the AppUtil slot parameter. The host stores these in .slot<N> files. */
static void h_firmware_slot_file_open(Cpu *c) {
	if (!A0 || !A1 || strcmp((const char *)G(A0), "savedata0:")) { RET(0x80100600u); return; }
	memset(G(A1), 0, 0x228);
	uint8_t p[SLOT_PARAM_SIZE];
	for (uint32_t id = 0; id < 256; id++) if (slot_read(id, p)) WR8(A1 + 0x28 + id, 1);
	RET(0);
}
static void h_firmware_slot_file_get_param(Cpu *c) {
	uint8_t p[SLOT_PARAM_SIZE];
	if (!A1 || A0 >= 256) { RET(0x80100600u); return; }
	if (!slot_read(A0, p)) { RET(0x80100641u); return; }
	extern void nova_save_translate_fields(char *subtitle, size_t subtitle_size, char *detail, size_t detail_size);
	nova_save_translate_fields((char *)(p + 0x44), 128, (char *)(p + 0xc4), 512);
	memset(G(A1), 0, 0x400);
	memcpy(G(A1), p, sizeof p);
	RET(0);
}
static void h_firmware_slot_file_close(Cpu *c) { RET(A0 ? 0 : 0x80100600u); }

/* The firmware plug-in uses a size-tagged AppMgr request.
 * Read the same slot metadata as the host picker and localize its display copy. */
static void h_firmware_slot_param(Cpu *c) {
	if (!A0 || RD32(A0) != 0x418 ||
	    memcmp(G(A0 + 0x408), "savedata0:", sizeof "savedata0:")) {
		RET(0x80100600u);
		return;
	}
	uint32_t slot = RD32(A0 + 4);
	uint8_t param[SLOT_PARAM_SIZE];
	if (!slot_read(slot, param)) { RET(0x80100641u); return; }
	extern void nova_save_translate_fields(char *subtitle, size_t subtitle_size, char *detail, size_t detail_size);
	nova_save_translate_fields((char *)(param + 0x44), 128, (char *)(param + 0xc4), 512);
	memcpy(G(A0 + 8), param, sizeof param);
	fprintf(stderr, "    firmware save slot %u metadata read\n", slot);
	RET(0);
}
static int slot_write(uint32_t id, uint32_t param) {   /* param: a guest SceAppUtilSaveDataSlotParam, or 0 to keep the slot's own; stamps the time */
	uint8_t p[SLOT_PARAM_SIZE];
	if (param) memcpy(p, G(param), SLOT_PARAM_SIZE); else slot_read(id, p);
	time_t now = time(0); struct tm tm; localtime_r(&now, &tm);
	uint16_t dt[6] = {(uint16_t)(tm.tm_year + 1900), (uint16_t)(tm.tm_mon + 1), (uint16_t)tm.tm_mday, (uint16_t)tm.tm_hour, (uint16_t)tm.tm_min, (uint16_t)tm.tm_sec};
	memcpy(p + 0x30c, dt, sizeof dt); memset(p + 0x318, 0, 4);
	char dir[1024]; snprintf(dir, sizeof dir, "%s/savedata0", player_save_root()); mkdir(dir, 0755);
	char m[1024]; slot_marker(id, m, sizeof m);
	FILE *f = fopen(m, "wb"); if (!f) return -1;
	fwrite(p, 1, SLOT_PARAM_SIZE, f); fclose(f);
	return 0;
}
static void h_save_slot_create(Cpu *c) { RET(slot_write(A0, A1) == 0 ? 0 : 0x80100600u); }   /* (slot id, SceAppUtilSaveDataSlotParam *, mount point) */
static void h_save_slot_delete(Cpu *c) { char m[1024]; slot_marker(A0, m, sizeof m); RET(unlink(m) == 0 ? 0 : 0x80100641u); }   /* SLOT_NOT_FOUND */
static void h_save_slot_param(Cpu *c) {   /* (slot id, SceAppUtilSaveDataSlotParam *, mount point) */
	uint8_t p[SLOT_PARAM_SIZE];
	if (!slot_read(A0, p)) { RET(0x80100641u); return; }   /* SLOT_NOT_FOUND */
	if (A1) memcpy(G(A1), p, SLOT_PARAM_SIZE);
	RET(0);
}
/* sceAppUtilSaveDataSlotSearch (work buffer, SceAppUtilSaveDataSlotSearchCond * {type +0: 0 slots that exist, 1 empty
 * ones; from +4; range +8}, result {hitNum +0, SceAppUtilSaveDataSlot *slotList +4 (16 bytes each: id, status, userParam,
 * emptyParam)}, mount point): the slots this game has in savedata0 (their .slot<N> markers). Phantasy Star Nova counts its
 * saves this way (0x81424d5c, a null list) before it offers CONTINUE; stubbed, a save would never have been seen. */
static void h_save_slot_search(Cpu *c) {
	if (!A1 || !A2) { RET(0x80100602u); return; }   /* (a missing parameter) */
	uint32_t type = RD32(A1), from = RD32(A1 + 4), range = RD32(A1 + 8), list = RD32(A2 + 4), hits = 0;
	if (range > 256) range = 256;
	uint8_t p[SLOT_PARAM_SIZE];
	for (uint32_t id = from; id < from + range; id++) {
		const int exists = slot_read(id, p);
		if (exists != (type == 0)) continue;
		if (list) {   /* (status and userParam from the slot's SceAppUtilSaveDataSlotParam: +0 and +0x304) */
			uint32_t st = 0, up = 0, e = list + 16 * hits;
			if (exists) { memcpy(&st, p, 4); memcpy(&up, p + 0x304, 4); }
			WR32(e, id); WR32(e + 4, st); WR32(e + 8, up); WR32(e + 12, 0);
		}
		hits++;
	}
	WR32(A2, hits);
	RET(0);
}
/* sceAppUtilSaveDataMount (title id, passcode): another title's save data, read with that title's passcode -- Phantasy
 * Star Nova looks for PSO2's (PCSG00141: a crew bonus) and its own demo's (an import offer). There are no other titles'
 * saves here: "not found" (the game only tests for nonzero, 0x81874258). Stubbed as success, it handed out the PSO2 bonus
 * and offered to import a demo save nobody has, a prompt that also stalled scripted runs (2026-11-18). */
static void h_save_mount_other(Cpu *c) {
	static int said; if (said++ < 4) fprintf(stderr, "    save data of another title (%s): not found -- no other title's saves here\n", A0 ? (char *)G(A0) : "?");
	RET(0x80100641u);   /* (SAVEDATA_SLOT_NOT_FOUND's code; the game reads only "not 0") */
}
static void h_save_slot_set_param(Cpu *c) { RET(slot_write(A0, A1) == 0 ? 0 : 0x80100600u); }   /* (slot id, param, mount point): a slot not yet created is created */
/* (SceAppUtilSaveDataFileSlot * (id +0, slotParam +4), SceAppUtilSaveDataFile[], count, mount point, *required KB)
 * file: path +0, buf +4, size +8, offset +16 (64-bit), mode +24; 64 bytes each */
static void h_save_data_save(Cpu *c) {
	char dir[1024]; snprintf(dir, sizeof dir, "%s/savedata0", player_save_root()); mkdir(dir, 0755);
	for (uint32_t i = 0; i < A2; i++) {
		uint32_t f = A1 + 64 * i, path = RD32(f), buf = RD32(f + 4), size = RD32(f + 8), mode = RD32(f + 24);
		uint64_t off = RD64(f + 16);
		char hp[1024]; snprintf(hp, sizeof hp, "%s/%s", dir, path ? (char *)G(path) : "");
		/* '\' separates as in io.c; the console creates the parent folders (Uncharted saves
		 * "slot_000/saves\checkpoint.bin" without a directory entry: every save failed until 2026-10-09) */
		for (char *q = hp + strlen(dir); *q; q++) if (*q == '\\') *q = '/';
		for (char *q = hp + strlen(dir) + 1; *q; q++) if (*q == '/') { *q = 0; mkdir(hp, 0755); *q = '/'; }
		if (mode == 2) { mkdir(hp, 0755); continue; }   /* a directory */
		int fd = open(hp, O_WRONLY | O_CREAT | (mode == 1 ? O_TRUNC : 0), 0644);
		if (fd < 0) { fprintf(stderr, "    save %s (mode %u, %u bytes): host open failed: %s\n", path ? (char *)G(path) : "", mode, size, strerror(errno)); continue; }
		if (buf && size) { gwatch_read_open(buf, size); pwrite(fd, G(buf), size, (off_t)off); }
		close(fd);
		fprintf(stderr, "    save %s: %u bytes at %llu from %#x\n", path ? (char *)G(path) : "", size, (unsigned long long)off, buf);
	}
	if (A0) slot_write(RD32(A0), RD32(A0 + 4));   /* the slot: created or updated, its param replaced when one is given */
	if (STK(0)) WR32(STK(0), 0);
	RET(0);
}
static void h_save_data_remove(Cpu *c) {   /* (slot, SceAppUtilSaveDataRemoveItem[] (44 bytes: path +0), count, mount) */
	for (uint32_t i = 0; i < A2; i++) {
		char hp[1024]; snprintf(hp, sizeof hp, "%s/savedata0/%s", player_save_root(), (char *)G(RD32(A1 + 0x2c * i)));
		for (char *q = hp + strlen(player_save_root()); *q; q++) if (*q == '\\') *q = '/';
		unlink(hp);
	}
	RET(0);
}

/* ---- the save-data dialog (SceSaveDataDialog): the system's own save / load / delete screens -- the
 * game's slots as a list to pick from, and the cards around it (Overwrite?, Saving..., Saving
 * complete). The console's state machine (Vita3K's SceCommonDialog.cpp is the reference): Init and
 * Continue open a step and its sub-status runs -- a list until a pick, a yes/no card until an
 * answer, a card with no buttons until the game's SubClose -- the game reads the answer with
 * GetResult once the sub-status reads FINISHED, Continues with the next step, then Finish and Term.
 * The overlay draws the step and answers it (savedlg.h, overlay.cpp's build_save_dialog). A card with
 * only an OK button never waits: it answers OK and its message shows as a toast. With no window
 * to answer in (a headless run, the regression gate), RECOMP_SAVE_DIALOG=auto or the setting
 * save_dialog=auto, every question answers itself: the list's focused row (RECOMP_SAVE_DIALOG_ROW=n: row n), YES -- the old behaviour,
 * which knew no list (until 2026-10-10 every dialog finished at once with YES and slot 0).
 * The host is lenient where the console returns an error for a call out of order (a Continue or
 * Finish before the step finished, a second Init): the step it asks for happens. */
enum { ST_NONE, ST_RUNNING, ST_FINISHED };   /* SceCommonDialogStatus */
static pthread_mutex_t sd_mu = PTHREAD_MUTEX_INITIALIZER;
static struct {
	int open, status, sub;              /* Init..Term; the dialog's status and its step's */
	int mode, disp, result, button;     /* GetResult: the step's mode, its result (0 OK, 1 canceled, 2 aborted, or an error), the button */
	uint32_t slot, userdata;            /* the slot acted on (the list's pick, a card's target slot) */
	int kind, seq, focus, percent;      /* what the overlay shows (savedlg.h) */
	char title[128], msg[512];
	int nrows; SaveDlgRow rows[256];
} sd;
/* a slot's text field (`bytes` long, or to a NUL) as display text: UTF-8 as the games write it (UTF-16LE
 * read as such should a game follow the SDK's header: a non-NUL first byte then a NUL), a line break as
 * a separator, and the trademark signs dropped (the overlay's bitmap font has no glyph for them) */
static void slot_text(const uint8_t *s, size_t bytes, char *out, size_t n) {
	size_t o = 0;
	const int wide = s && bytes >= 2 && s[0] && !s[1];
	for (size_t i = 0; s && i < bytes && o + 4 < n; ) {
		uint32_t u;
		if (wide) { if (i + 1 >= bytes || !(u = s[i] | s[i + 1] << 8)) break; i += 2; }
		else {
			if (!s[i]) break;
			const uint8_t b = s[i]; int k = b < 0x80 ? 1 : b >= 0xf0 ? 4 : b >= 0xe0 ? 3 : 2;
			if (i + k > bytes) break;
			u = k == 1 ? b : k == 2 ? (b & 0x1fu) << 6 | (s[i + 1] & 0x3fu) : k == 3 ? (b & 0x0fu) << 12 | (s[i + 1] & 0x3fu) << 6 | (s[i + 2] & 0x3fu)
			  : (b & 0x07u) << 18 | (s[i + 1] & 0x3fu) << 12 | (s[i + 2] & 0x3fu) << 6 | (s[i + 3] & 0x3fu);
			i += (size_t)k;
		}
		if (u == 0x2122 || u == 0xae || u == 0xa9) continue;   /* (TM) (R) (C) */
		if (u == '\n' || u == '\r') { if (o && out[o - 1] != ' ') { memcpy(out + o, "  -  ", 5); o += 5; } continue; }
		if (u < 0x80) out[o++] = (char)u;
		else if (u < 0x800) { out[o++] = (char)(0xc0 | u >> 6); out[o++] = (char)(0x80 | (u & 0x3f)); }
		else if (u < 0x10000) { out[o++] = (char)(0xe0 | u >> 12); out[o++] = (char)(0x80 | (u >> 6 & 0x3f)); out[o++] = (char)(0x80 | (u & 0x3f)); }
		else { out[o++] = (char)(0xf0 | u >> 18); out[o++] = (char)(0x80 | (u >> 12 & 0x3f)); out[o++] = (char)(0x80 | (u >> 6 & 0x3f)); out[o++] = (char)(0x80 | (u & 0x3f)); }
	}
	while (o >= 5 && !memcmp(out + o - 5, "  -  ", 5)) o -= 5;
	if (n) out[o] = 0;
}
/* one row of the list: the slot's saved data, or the game's "new saved data" row (empty: the slot's
 * SceAppUtilSaveDataSlotEmptyParam, title +0). An empty slot the game offers no such row for isn't
 * listed (the console's list) */
static void sd_add_row(uint32_t id, uint32_t empty) {
	uint8_t p[SLOT_PARAM_SIZE]; SaveDlgRow *r = &sd.rows[sd.nrows];
	memset(r, 0, sizeof *r); r->id = id;
	if ((r->exists = slot_read(id, p))) {
		slot_text(p + 0x4, 64, r->title, sizeof r->title);
		const char *title_id = getenv("RECOMP_TITLE");
		if (title_id && !strcmp(title_id, "PCSG00351")) {
			/* Nova stores UTF-8, including the literal player name. */
			memcpy(r->sub, p + 0x44, 128);
			r->can_delete = id < 255;   /* Nova uses slot 255 for system data. */
		} else {
			slot_text(p + 0x44, 128, r->sub, sizeof r->sub);
		}
		const uint8_t *d = p + 0xc4; while (*d == '\n' || *d == '\r') d++;   /* (Uncharted's detail starts with a line break) */
		slot_text(d, 512 - (size_t)(d - (p + 0xc4)), r->detail, sizeof r->detail);
		if (!r->title[0]) snprintf(r->title, sizeof r->title, "Saved data %u", id);
		uint16_t t[6]; memcpy(t, p + 0x30c, sizeof t);
		if (t[0]) snprintf(r->date, sizeof r->date, "%04u-%02u-%02u %02u:%02u", t[0], t[1], t[2], t[3], t[4]);
		else {   /* a marker from before slots kept their param: the file's own time */
			char m[1024]; struct stat st; slot_marker(id, m, sizeof m);
			if (!stat(m, &st)) { struct tm tm; localtime_r(&st.st_mtime, &tm); strftime(r->date, sizeof r->date, "%Y-%m-%d %H:%M", &tm); }
		}
	} else {
		if (!empty) return;
		uint32_t t = RD32(empty);
		if (t) slot_text(G(t), 64, r->title, sizeof r->title);
		if (!r->title[0]) snprintf(r->title, sizeof r->title, "New Saved Data");
	}
	sd.nrows++;
}
/* the row the list opens on (SceSaveDataDialogListParam focusPos +8, focusId +0xc): 0 the list's head,
 * 1 its tail, 2/3 the first/last empty row, 4/5 the first/last saved one, 6/7 the newest/oldest
 * saved one, 8 the row of focusId */
static int sd_focus(uint32_t lp) {
	uint32_t pos = RD32(lp + 8), fid = RD32(lp + 0xc); int f = -1;
	for (int i = 0; i < sd.nrows; i++) {
		const SaveDlgRow *r = &sd.rows[i]; int take = 0;
		switch (pos) {
		case 0: take = f < 0; break;
		case 1: take = 1; break;
		case 2: take = !r->exists && f < 0; break;
		case 3: take = !r->exists; break;
		case 4: take = r->exists && f < 0; break;
		case 5: take = r->exists; break;
		case 6: take = r->exists && (f < 0 || strcmp(r->date, sd.rows[f].date) > 0); break;
		case 7: take = r->exists && (f < 0 || strcmp(r->date, sd.rows[f].date) < 0); break;
		case 8: take = r->id == fid; break;
		}
		if (take) f = i;
	}
	return f < 0 ? 0 : f;
}
static const char *sd_verb(const char *save, const char *load, const char *del) { return sd.disp == 2 ? load : sd.disp == 3 ? del : save; }
static int sd_auto(void) {
	extern int overlay_draws_hud(void);
	if (!overlay_draws_hud()) return 1;   /* no window to answer in */
	const char *e = getenv("RECOMP_SAVE_DIALOG");
	if (e) return !strcmp(e, "auto");
	char b[16]; return !strcmp(settings_str("save_dialog", "ask", b, sizeof b), "auto");
}
static void sd_answer(int choice) {   /* (locked) the player's answer to the running step; savedlg.h */
	if (sd.kind == SAVEDLG_LIST && choice >= 0 && choice < sd.nrows) { sd.slot = sd.rows[choice].id; sd.result = 0; sd.button = 0; }
	else if (sd.kind == SAVEDLG_YESNO && (choice == SAVEDLG_YES || choice == SAVEDLG_NO)) { sd.result = 0; sd.button = choice; }
	else if (sd.kind == SAVEDLG_LIST || sd.kind == SAVEDLG_YESNO) { sd.result = 1; sd.button = 0; }   /* USER_CANCELED, button INVALID */
	else return;
	fprintf(stderr, "    save dialog: %s -> %s (slot %u)\n", sd.kind == SAVEDLG_LIST ? "list" : "yes/no", sd.result ? "canceled" : sd.kind == SAVEDLG_LIST ? "picked" : sd.button == SAVEDLG_YES ? "yes" : "no", sd.slot);
	sd.sub = ST_FINISHED; sd.kind = SAVEDLG_NONE;
}
/* (locked) open the step SceSaveDataDialogParam `prm` asks for: mode +0x50 (1 FIXED, 2 LIST, 3 USER_MSG,
 * 4 SYSTEM_MSG, 5 ERROR_CODE, 6 PROGRESS_BAR), dispType +0x54 (1 save, 2 load, 3 delete), the mode's
 * own param +0x58..+0x6c, userdata +0x78. Each card names its slot (a SceAppUtilSaveDataSlot: id +0). */
static void sd_step(uint32_t prm, int init) {
	int mode = (int)RD32(prm + 0x50), disp = (int)RD32(prm + 0x54);
	sd.mode = mode; if (disp || init) sd.disp = disp;
	if (init) sd.userdata = RD32(prm + 0x78);
	sd.status = sd.sub = ST_RUNNING; sd.result = 0; sd.button = 0;
	sd.kind = SAVEDLG_NONE; sd.percent = -1; sd.title[0] = sd.msg[0] = 0; sd.seq++;
	uint32_t target = 0; int buttons = -1;   /* a card's slot; its buttons (0 none, 1 OK, 2 yes/no) */
	static const char *const sysmsg[] = {0, "There is no saved data.", 0, "Do you want to overwrite this saved data?", 0, 0, 0, 0, "The saved data is corrupted.", "There is not enough free space to save.", 0, 0, "There is no saved data that can be used with this application."};
	switch (mode) {
	case 1: target = RD32(prm + 0x58); sd.sub = ST_FINISHED; break;   /* FIXED (targetSlot +0): nothing to browse, done at once */
	case 2: {   /* LIST: slotList +0, slotListSize +4, focus +8/+0xc, listTitle +0x10 */
		uint32_t lp = RD32(prm + 0x5c); if (!lp) break;
		uint32_t list = RD32(lp), n = RD32(lp + 4), lt = RD32(lp + 0x10);
		if (n > 256) n = 256;
		snprintf(sd.title, sizeof sd.title, "%s", lt ? (const char *)G(lt) : sd_verb("Save", "Load", "Delete"));
		sd.nrows = 0;
		for (uint32_t i = 0; i < n; i++) if (RD32(list + 16 * i) >= 256) {   /* an id past the 256 slots: the step fails at once, slot -1 */
			sd.slot = ~0u; sd.result = (int)0x80100b01; sd.sub = ST_FINISHED; return;   /* SCE_SAVEDATA_DIALOG_ERROR_PARAM */
		}
		for (uint32_t i = 0; i < n; i++) sd_add_row(RD32(list + 16 * i), RD32(list + 16 * i + 12));
		sd.focus = sd_focus(lp);
		sd.kind = SAVEDLG_LIST;
		break;
	}
	case 3: {   /* USER_MSG: buttonType +0 (0 OK, 1 yes/no, 2 none), msg +4 (UTF-8), targetSlot +8 */
		uint32_t up = RD32(prm + 0x60); if (!up) break;
		uint32_t bt = RD32(up), m = RD32(up + 4); target = up + 8;
		snprintf(sd.msg, sizeof sd.msg, "%s", m ? (const char *)G(m) : "");
		buttons = bt == 0 ? 1 : bt == 1 ? 2 : 0;
		break;
	}
	case 4: {   /* SYSTEM_MSG: sysMsgType +0, value +4, targetSlot +8 */
		uint32_t sp = RD32(prm + 0x64); if (!sp) break;
		if (init && !disp) { sd.slot = ~0u; sd.result = (int)0x80100b01; sd.status = ST_FINISHED; return; }   /* (the console: an Init with no dispType ends the dialog with ERROR_PARAM; a Continue's 0 keeps the dialog's) */
		uint32_t type = RD32(sp); target = sp + 8;
		switch (type) {
		case 2: snprintf(sd.msg, sizeof sd.msg, "%s", sd_verb("Do you want to save?", "Do you want to load this saved data?", "Do you want to delete this saved data?")); buttons = 2; break;   /* CONFIRM */
		case 3: buttons = 2; break;   /* OVERWRITE */
		case 5: snprintf(sd.msg, sizeof sd.msg, "%s", sd_verb("Saving... Do not power off the system.", "Loading...", "Please wait...")); buttons = 0; break;   /* PROGRESS */
		case 6: snprintf(sd.msg, sizeof sd.msg, "%s", sd_verb("Saving complete.", "Loading complete.", "Deletion complete.")); buttons = 1; break;   /* FINISHED */
		case 7: snprintf(sd.msg, sizeof sd.msg, "%s", sd_verb("Do you want to cancel saving?", "Do you want to cancel loading?", "Do you want to cancel deleting?")); buttons = 2; break;   /* CONFIRM_CANCEL */
		case 4: buttons = 0; break;   /* NOSPACE: an information card */
		default: buttons = 1; break;  /* NODATA, FILE_CORRUPTED, NOSPACE_CONTINUABLE, NODATA_IMPORT */
		}
		if (!sd.msg[0] && type < sizeof sysmsg / sizeof *sysmsg && sysmsg[type]) snprintf(sd.msg, sizeof sd.msg, "%s", sysmsg[type]);
		break;
	}
	case 5: {   /* ERROR_CODE: errorCode +0, targetSlot +4 */
		uint32_t ep = RD32(prm + 0x68); if (!ep) break;
		snprintf(sd.msg, sizeof sd.msg, "An error occurred. (%08X)", RD32(ep)); target = ep + 4; buttons = 1;
		break;
	}
	case 6: {   /* PROGRESS_BAR: msg +0x3c, targetSlot +0x40 */
		uint32_t pp = RD32(prm + 0x6c); if (!pp) break;
		uint32_t m = RD32(pp + 0x3c); target = pp + 0x40;
		snprintf(sd.msg, sizeof sd.msg, "%s", m ? (const char *)G(m) : sd_verb("Saving...", "Loading...", "Please wait..."));
		sd.percent = 0; buttons = 0;
		break;
	}
	}
	if (target) sd.slot = RD32(target);
	if (buttons == 2) sd.kind = SAVEDLG_YESNO;
	else if (buttons == 0) sd.kind = SAVEDLG_WAIT;
	else if (buttons == 1) {   /* OK alone: answered at once, the message as a toast */
		extern void overlay_toast_titled(const char *title, const char *body, double seconds);
		sd.button = 1; sd.sub = ST_FINISHED;
		if (sd.msg[0]) overlay_toast_titled("Saves", sd.msg, 3.0);
	}
	fprintf(stderr, "    save dialog: %s mode %d (%s), slot %d%s%s%s\n", init ? "init" : "continue", mode, sd_verb("save", "load", "delete"), (int)sd.slot,
		sd.kind == SAVEDLG_LIST ? ", a list" : "", sd.msg[0] ? ": " : "", sd.msg);
	if (sd.kind == SAVEDLG_LIST) for (int i = 0; i < sd.nrows; i++)
		fprintf(stderr, "      %c slot %u: %s%s%s%s%s  %s\n", i == sd.focus ? '>' : ' ', sd.rows[i].id, sd.rows[i].title, sd.rows[i].sub[0] ? " / " : "", sd.rows[i].sub,
			sd.rows[i].detail[0] ? " / " : "", sd.rows[i].detail, sd.rows[i].exists ? sd.rows[i].date : "(empty)");
	if ((sd.kind == SAVEDLG_LIST || sd.kind == SAVEDLG_YESNO) && sd_auto())
		sd_answer(sd.kind == SAVEDLG_YESNO ? SAVEDLG_YES : !sd.nrows ? SAVEDLG_CANCEL
		          : getenv("RECOMP_SAVE_DIALOG_ROW") ? atoi(getenv("RECOMP_SAVE_DIALOG_ROW")) % sd.nrows : sd.focus);   /* (a test's pick: that row) */
}
static void h_save_dlg_init(Cpu *c) {
	if (!A0) { RET(0x80020402u); return; }   /* SCE_COMMON_DIALOG_ERROR_NULL */
	pthread_mutex_lock(&sd_mu); sd.open = 1; sd_step(A0, 1); pthread_mutex_unlock(&sd_mu);
	RET(0);
}
static void h_save_dlg_continue(Cpu *c) {
	if (!A0) { RET(0x80020402u); return; }
	pthread_mutex_lock(&sd_mu);
	int ok = sd.open && sd.status == ST_RUNNING;
	if (ok) sd_step(A0, 0);
	pthread_mutex_unlock(&sd_mu);
	RET(ok ? 0 : 0x80020404u);   /* NOT_RUNNING */
}
/* the dialog's status: RUNNING until Finish, then FINISHED until Term */
static void h_save_dlg_status(Cpu *c) {
	pthread_mutex_lock(&sd_mu); int s = !sd.open || (sd.status != ST_RUNNING && sd.sub != ST_RUNNING) ? ST_NONE : sd.status; pthread_mutex_unlock(&sd_mu);
	RET(s);
}
static void h_save_dlg_substatus(Cpu *c) {   /* the step's: RUNNING while the player (or the game's card) has it, FINISHED once answered */
	pthread_mutex_lock(&sd_mu); int s = !sd.open || sd.status != ST_RUNNING ? ST_NONE : sd.sub; pthread_mutex_unlock(&sd_mu);
	RET(s);
}
/* (SceSaveDataDialogResult *): mode +0, result +4, buttonId +8, slotId +0xc, slotInfo +0x10 (isExist +0,
 * slotParam * +4), userdata +0x14 -- once the step or the dialog has finished */
static void h_save_dlg_result(Cpu *c) {
	if (!A0) { RET(0x80020402u); return; }
	pthread_mutex_lock(&sd_mu);
	int done = sd.open && (sd.status == ST_FINISHED || sd.sub == ST_FINISHED);
	if (done) {
		WR32(A0, sd.mode); WR32(A0 + 4, sd.result); WR32(A0 + 8, sd.button); WR32(A0 + 0xc, sd.slot); WR32(A0 + 0x14, sd.userdata);
		uint32_t si = RD32(A0 + 0x10);
		if (si) {
			uint8_t p[SLOT_PARAM_SIZE]; int ex = sd.slot < 256 && slot_read(sd.slot, p);
			WR32(si, ex); uint32_t sp = RD32(si + 4);
			if (sp && ex) memcpy(G(sp), p, SLOT_PARAM_SIZE);
		}
	}
	pthread_mutex_unlock(&sd_mu);
	RET(done ? 0 : 0x80020410u);   /* NOT_FINISHED */
}
static void h_save_dlg_finish(Cpu *c) {   /* the dialog's last step is done: FINISHED until Term */
	pthread_mutex_lock(&sd_mu);
	int ok = sd.open && sd.status == ST_RUNNING;
	if (ok) { sd.status = ST_FINISHED; sd.sub = ST_RUNNING; sd.kind = SAVEDLG_NONE; sd.percent = -1; }
	pthread_mutex_unlock(&sd_mu);
	RET(ok ? 0 : 0x80020404u);
}
static void h_save_dlg_term(Cpu *c) { pthread_mutex_lock(&sd_mu); sd.open = 0; sd.status = sd.sub = ST_NONE; sd.kind = SAVEDLG_NONE; pthread_mutex_unlock(&sd_mu); RET(0); }
static void h_save_dlg_abort(Cpu *c) {
	pthread_mutex_lock(&sd_mu); sd.result = 2; sd.button = 0; sd.open = 0; sd.status = ST_FINISHED; sd.kind = SAVEDLG_NONE; pthread_mutex_unlock(&sd_mu);   /* ABORTED */
	RET(0);
}
static void h_save_dlg_subclose(Cpu *c) {   /* the game ends a step itself (a card with no buttons) */
	pthread_mutex_lock(&sd_mu);
	int ok = sd.open && sd.sub == ST_RUNNING;
	if (ok) { sd.sub = ST_FINISHED; sd.result = 0; sd.button = 0; sd.kind = SAVEDLG_NONE; }
	pthread_mutex_unlock(&sd_mu);
	RET(ok ? 0 : 0x80020404u);
}
static void h_save_dlg_bar_inc(Cpu *c) { pthread_mutex_lock(&sd_mu); if (sd.percent >= 0) { sd.percent += (int)A1; if (sd.percent > 100) sd.percent = 100; } pthread_mutex_unlock(&sd_mu); RET(0); }   /* (target, delta) */
static void h_save_dlg_bar_set(Cpu *c) { pthread_mutex_lock(&sd_mu); if (sd.percent >= 0) sd.percent = A1 > 100 ? 100 : (int)A1; pthread_mutex_unlock(&sd_mu); RET(0); }   /* (target, rate) */
int savedlg_view(SaveDlgView *v) {
	pthread_mutex_lock(&sd_mu);
	int live = sd.open && sd.status == ST_RUNNING && sd.sub == ST_RUNNING;
	v->kind = live ? sd.kind : SAVEDLG_NONE; v->seq = sd.seq; v->disp = sd.disp; v->focus = sd.focus; v->percent = sd.percent;
	memcpy(v->title, sd.title, sizeof v->title); memcpy(v->msg, sd.msg, sizeof v->msg);
	v->nrows = sd.nrows; v->rows = sd.rows;
	return v->kind;
}
void savedlg_release(void) { pthread_mutex_unlock(&sd_mu); }
void savedlg_answer(int seq, int choice) {
	pthread_mutex_lock(&sd_mu);
	if (sd.open && seq == sd.seq && sd.status == ST_RUNNING && sd.sub == ST_RUNNING) sd_answer(choice);
	pthread_mutex_unlock(&sd_mu);
}

/* The recovery directory stays on the save filesystem. A
 * failed marker move puts the payload back before the picker changes. */
static int nova_archive_save(uint32_t id, char *msg, size_t n) {
	char root[1024], marker[1024], data[1024], recovery[1152], target_marker[1200], target_data[1200];
	if (snprintf(root, sizeof root, "%s/deleted_saves", player_save_root()) >= (int)sizeof root ||
	    snprintf(data, sizeof data, "%s/savedata0/savedata%u.bin", player_save_root(), id) >= (int)sizeof data) {
		snprintf(msg, n, "The save path is too long.");
		return -1;
	}
	slot_marker(id, marker, sizeof marker);
	struct stat st;
	if (stat(marker, &st) || !S_ISREG(st.st_mode)) {
		snprintf(msg, n, "This slot's metadata is unavailable.");
		return -1;
	}
	const int have_data = stat(data, &st) == 0;
	if ((have_data && !S_ISREG(st.st_mode)) || (!have_data && errno != ENOENT)) {
		snprintf(msg, n, "This slot's save file is unavailable.");
		return -1;
	}
	if (mkdir(root, 0755) && (errno != EEXIST || stat(root, &st) || !S_ISDIR(st.st_mode))) {
		snprintf(msg, n, "Couldn't open the deleted saves folder.");
		return -1;
	}
	const long long stamp = (long long)time(NULL);
	unsigned attempt = 0;
	do {
		snprintf(recovery, sizeof recovery, "%s/slot-%u-%lld-%u", root, id, stamp, ++attempt);
		if (mkdir(recovery, 0755) == 0) break;
		if (errno != EEXIST || attempt == 100) {
			snprintf(msg, n, "Couldn't create a recovery folder.");
			return -1;
		}
	} while (1);
	snprintf(target_data, sizeof target_data, "%s/savedata%u.bin", recovery, id);
	snprintf(target_marker, sizeof target_marker, "%s/.slot%u", recovery, id);
	if (have_data && rename(data, target_data)) {
		rmdir(recovery);
		snprintf(msg, n, "Couldn't move this slot's save file.");
		return -1;
	}
	if (rename(marker, target_marker)) {
		if (have_data && rename(target_data, data)) {
			snprintf(msg, n, "Couldn't finish deleting. The save file is in %s.", recovery);
			fprintf(stderr, "    Nova save delete rollback failed: %s\n", recovery);
			return -1;
		}
		rmdir(recovery);
		snprintf(msg, n, "Couldn't move this slot's metadata.");
		return -1;
	}
	snprintf(msg, n, "Slot %u moved to deleted_saves.", id + 1);
	fprintf(stderr, "    Nova save slot %u moved to %s\n", id, recovery);
	return 0;
}

int savedlg_delete_nova_slot(int seq, uint32_t id, char *msg, size_t n) {
	pthread_mutex_lock(&sd_mu);
	int row = 0;
	while (row < sd.nrows && (sd.rows[row].id != id || !sd.rows[row].can_delete)) row++;
	int result = -1;
	if (sd.open && seq == sd.seq && sd.status == ST_RUNNING && sd.sub == ST_RUNNING &&
	    sd.kind == SAVEDLG_LIST && (sd.disp == 1 || sd.disp == 2) && row < sd.nrows) {
		result = nova_archive_save(id, msg, n);
		if (result == 0) {
			if (sd.disp == 1) {
				SaveDlgRow *r = &sd.rows[row];
				memset(r, 0, sizeof *r);
				r->id = id;
				snprintf(r->title, sizeof r->title, "New Saved Data");
			} else {
				sd.nrows--;
				memmove(&sd.rows[row], &sd.rows[row + 1], (size_t)(sd.nrows - row) * sizeof sd.rows[0]);
				if (sd.focus >= sd.nrows) sd.focus = sd.nrows ? sd.nrows - 1 : 0;
			}
		}
	} else {
		snprintf(msg, n, "That slot is no longer available.");
	}
	pthread_mutex_unlock(&sd_mu);
	return result;
}

/* ---- trophies: a context and a handle that accept everything */
static void h_trophy_create(Cpu *c) { if (A0) WR32(A0, 1); RET(0); }

/* system events (suspend/resume and the like): none ever arrives; the real call returns an error
 * when the queue is empty, which ends a game's drain loop */
static void h_receive_system_event(Cpu *c) { RET(0x80802016u); }

/* system settings (id, *value): 1 language (1 English US), 2 enter button (1 cross), 4 date format
 * (0 YYYY/MM/DD), 5 time format (0 12-hour), 6 time zone (0 minutes: UTC, which is what the host's
 * RTC reports as local time too), 7 summer time (0 off); 3 is the user name, a string. Anything else
 * is SCE_APPUTIL_ERROR_PARAMETER, as on the console. */
static void h_system_param_int(Cpu *c) {
	if (A0 < 1 || A0 > 7 || A0 == 3 || !A1) { RET(0x80100600u); return; }
	WR32(A1, A0 == 1 || A0 == 2 ? 1 : 0); RET(0);
}
/* (id, buffer, size): only the user name (3) is a string -- "Player" (RECOMP_USERNAME overrides),
 * truncated to the buffer like strncpy plus a terminator; Killzone asks for it at boot (17 bytes:
 * the SDK's 16-character limit) */
static void h_system_param_string(Cpu *c) {
	if (A0 != 3 || !A1 || !A2) { RET(0x80100600u); return; }
	const char *name = getenv("RECOMP_USERNAME") ? getenv("RECOMP_USERNAME") : "Player";
	size_t n = strlen(name); if (n > 16) n = 16; if (n > A2 - 1) n = A2 - 1;
	memcpy(G(A1), name, n); WR8(A1 + (uint32_t)n, 0);
	RET(0);
}
/* app events (a LiveArea launch argument, an invitation, a Near gift): none ever arrives on the host.
 * ReceiveAppEvent with an empty queue fails (the AppMgr's "no parameter in this state"), so a game's
 * drain loop ends and it takes nothing as an event; parsing an event it can never have received is
 * the parse error */
static void h_receive_app_event(Cpu *c) { if (A0) memset(G(A0), 0, 0x404); RET(0x80802013u); }   /* SceAppUtilAppEventParam: type + 1 KiB of data */
static void h_app_event_parse(Cpu *c) { RET(0x80100620u); }   /* SCE_APPUTIL_ERROR_APPEVENT_PARSE_INVALID_DATA */
/* SceKernelOpenPsId: the console's 16-byte id exposed to games (save ownership, online keys -- Mirage's moderation bans
 * by a machine id made from it, sent with the login). One per install: random, made once and kept (the shared settings'
 * "open_psid"), so a ban or a server's record is one player's, never every Nativ player's -- it was one fixed id for all.
 * A game that already has saves keeps the old fixed id (written to its own settings), in case it tied them to the
 * console; so does a scripted run (RECOMP_HEADLESS), for the gate. */
static void open_psid(uint8_t id[16]) {
	static const uint8_t fixed[16] = {0x56, 0x52, 0x45, 0x43, 0x4f, 0x4d, 0x50, 0x2d, 0x48, 0x4f, 0x53, 0x54, 0x00, 0x00, 0x00, 0x01};   /* "VRECOMP-HOST" */
	static uint8_t cur[16]; static int have;
	if (have) { memcpy(id, cur, 16); return; }
	char b[48]; settings_str("open_psid", "", b, sizeof b);
	int ok = strlen(b) == 32;
	for (int i = 0; ok && i < 16; i++) { unsigned v; ok = sscanf(b + 2 * i, "%2x", &v) == 1; cur[i] = (uint8_t)v; }
	if (!ok) {
		char dir[1024]; snprintf(dir, sizeof dir, "%s/savedata0", player_save_root());
		int saves = 0;
		DIR *d = opendir(dir);
		if (d) { struct dirent *e; while ((e = readdir(d))) saves |= e->d_name[0] != '.'; closedir(d); }
		int keep = saves || getenv("RECOMP_HEADLESS");
		if (keep) memcpy(cur, fixed, 16); else plat_random(cur, 16);
		for (int i = 0; i < 16; i++) snprintf(b + 2 * i, 3, "%02x", cur[i]);
		if (!getenv("RECOMP_HEADLESS")) { if (keep) settings_set_own("open_psid", b); else settings_set_str("open_psid", b); settings_save(); }
	}
	have = 1; memcpy(id, cur, 16);
}
static void h_open_psid(Cpu *c) {
	if (!A0) { RET(0x80020006u); return; }   /* ILLEGAL_ADDR */
	uint8_t id[16]; open_psid(id);
	memcpy(G(A0), id, 16); RET(0);
}

/* ---- SceAvPlayer (movies: Killzone's intro): no video decoder exists on the host, so the player
 * fails honestly -- Init gives a handle (it only allocates on the console), adding a source fails
 * with INVALID_PARAM, the player is never active and never has a frame. A game then skips the movie
 * as it would a missing file (Killzone's player update returns "done" when AddSource fails). */
static void h_avplayer_init(Cpu *c) { uint32_t h = guest_alloc(16, 16); memset(G(h), 0, 16); RET(A0 ? h : 0); }   /* (SceAvPlayerInitData *) */
static void h_avplayer_add_source(Cpu *c) {
	static int said; if (!said++) fprintf(stderr, "    avplayer: %s: no video decoder -- the source is refused\n", A1 ? (char *)G(A1) : "(null)");
	RET(0x806a0001u);   /* SCE_AVPLAYER_ERROR_INVALID_PARAM */
}
static void h_avplayer_frame(Cpu *c) { if (A1) memset(G(A1), 0, 0x20); RET(0); }   /* (handle, SceAvPlayerFrameInfo *): false, nothing decoded */
static void h_avplayer_no_stream(Cpu *c) { RET(0x806a0001u); }   /* GetStreamInfo / EnableStream / JumpToTime / Start with no source */
static void h_avplayer_time(Cpu *c) { c->r[0] = 0; c->r[1] = 0; }   /* CurrentTime: a 64-bit 0 ms */
static void h_app_state(Cpu *c) { memset(G(A0), 0, A1); RET(0); }   /* (SceAppMgrAppState *, size, version): nothing pending */
static void h_zero_ok(Cpu *c) { RET(0); }
/* sceAppMgrAppParamGetString(pid, param, buf, size): param 12 is the title id (np_matching2 asks for it); the others unknown */
static void h_app_param_string(Cpu *c) {
	if (!A2 || !A3) { RET(0x80800001u); return; }
	if (A1 != 12) { static int said; if (!said++) fprintf(stderr, "    sceAppMgrAppParamGetString: param %u unknown\n", A1); RET(0x80800001u); return; }
	const char *t = getenv("RECOMP_TITLE"); snprintf((char *)G(A2), A3, "%s", t ? t : "");
	RET(0);
}
/* ---- the text entry dialog (SceImeDialog): the system keyboard over the game (Phantasy Star Nova names its character
 * with it). For now it answers at once, as if the player pressed Enter on the text shown: the game's initial text when
 * it gives one, else RECOMP_IME_TEXT, else "Nova" -- cut to the dialog's maximum length. (Stubbed, Init/GetStatus
 * returned 0: the game waited forever for a dialog that never finished.) SceImeDialogParam: maxTextLength +0x2c,
 * initialText +0x30 and inputTextBuffer +0x34 (UTF-16); SceImeDialogResult: result +0, button +4 (ENTER 2). */
static int ime_state;   /* 0 none, 2 finished (SCE_COMMON_DIALOG_STATUS_*) */
/* the text a keyboard answers with: the game's initial text, else RECOMP_IME_TEXT, else "Nova", cut to maxlen, written
 * (UTF-16, terminated) into buf; its length, and an ASCII copy for the log */
static uint32_t ime_fill(uint32_t init, uint32_t buf, uint32_t maxlen, char shown[64]) {
	uint16_t text[64]; uint32_t n = 0;
	if (init) while (n < 63 && RD16(init + 2 * n)) { text[n] = RD16(init + 2 * n); n++; }
	if (!n) { const char *d = getenv("RECOMP_IME_TEXT"); if (!d || !*d) d = "Nova"; while (n < 63 && d[n]) { text[n] = (uint8_t)d[n]; n++; } }   /* (ASCII: a name typed on a keyboard) */
	if (maxlen && n > maxlen) n = maxlen;
	if (buf) { for (uint32_t k = 0; k < n; k++) WR16(buf + 2 * k, text[k]); WR16(buf + 2 * n, 0); }
	for (uint32_t k = 0; k < n; k++) shown[k] = text[k] < 0x80 ? (char)text[k] : '?';
	shown[n] = 0;
	return n;
}
static void h_ime_dialog_init(Cpu *c) {
	if (!A0) { RET(0x80020402u); return; }   /* SCE_COMMON_DIALOG_ERROR_NULL */
	if (ime_state) { RET(0x80020001u); return; }   /* SCE_COMMON_DIALOG_ERROR_BUSY */
	char shown[64]; uint32_t maxlen = RD32(A0 + 0x2c), n = ime_fill(RD32(A0 + 0x30), RD32(A0 + 0x34), maxlen, shown);
	fprintf(stderr, "    ime dialog: answered at once with \"%s\" (%u chars, max %u)\n", shown, n, maxlen);
	ime_state = 2;
	RET(0);
}

/* ---- the in-game keyboard (SceIme: sceImeOpen / sceImeUpdate / sceImeClose). Phantasy Star Nova names its character
 * with it, through a table of function pointers (so no call site names these imports). SceImeParam as the game fills
 * it (0x81216226..0x81216272): arg +0x20, handler +0x24, initialText +0x2c, maxTextLength +0x30, inputTextBuffer +0x34.
 * The game then polls sceImeUpdate for events to its handler (0x812163b8's switch): 0 OPEN, 1 UPDATE_TEXT (sets its
 * "text changed" flag), 2 caret and 3 size (ignored), 4 PRESS_CLOSE and 5 PRESS_ENTER (both: finished). Its per-frame
 * code copies the text only while the keyboard is still open after an UPDATE_TEXT, so the answer comes over separate
 * updates as if typed: OPEN, then the text (ime_fill) with UPDATE_TEXT, then PRESS_ENTER a few updates later.
 * Nova uses an interactive overlay; other titles and headless runs keep the original automatic answer. */
/* The UI only exchanges snapshots and UTF-8 with this bridge. Guest memory and callbacks stay on the guest thread. */
#define IME_UNITS 1023
static pthread_mutex_t ime_mu = PTHREAD_MUTEX_INITIALIZER;
static struct {
 int open, step, interactive, response, phase; unsigned seq;
 uint32_t arg, handler, init, maxlen, buf, ev;
 uint16_t initial[IME_UNITS + 1], result[IME_UNITS + 1];
 char text[4096];
} ime;
static uint32_t ime_limit(void) { return ime.maxlen < IME_UNITS ? ime.maxlen : IME_UNITS; }
static void ime_to_utf8(const uint16_t *src, char *dst, size_t cap) {
 size_t o = 0;
 for (size_t i = 0; src[i]; i++) {
  uint32_t cp = src[i];
  if (cp >= 0xd800 && cp <= 0xdbff && src[i+1] >= 0xdc00 && src[i+1] <= 0xdfff) cp = 0x10000 + ((cp-0xd800)<<10) + (src[++i]-0xdc00);
  else if (cp >= 0xd800 && cp <= 0xdfff) cp = 0xfffd;
  unsigned n = cp < 0x80 ? 1 : cp < 0x800 ? 2 : cp < 0x10000 ? 3 : 4;
  if (o + n >= cap) break;
  if (n == 1) dst[o++] = (char)cp;
  else { for (unsigned j = n-1; j; j--) dst[o+j] = (char)(0x80 | (cp & 63)), cp >>= 6; dst[o] = (char)((n == 2 ? 0xc0 : n == 3 ? 0xe0 : 0xf0) | cp); o += n; }
 }
 dst[o] = 0;
}
/* Invalid UTF-8 is replaced; supplementary characters are never split at the guest limit. */
static void ime_from_utf8(const char *s, uint16_t *out, uint32_t limit) {
 const unsigned char *p = (const unsigned char *)s; uint32_t o = 0;
 while (*p && o < limit) {
  uint32_t cp; unsigned n; unsigned char b = *p;
  if (b < 0x80) cp = b, n = 1;
  else if (b >= 0xc2 && b <= 0xdf) cp = b & 31, n = 2;
  else if (b >= 0xe0 && b <= 0xef) cp = b & 15, n = 3;
  else if (b >= 0xf0 && b <= 0xf4) cp = b & 7, n = 4;
  else { cp = 0xfffd; n = 1; }
  if (n > 1) {
   unsigned j; for (j = 1; j < n && p[j] && (p[j] & 0xc0) == 0x80; j++) cp = (cp << 6) | (p[j] & 63);
   if (j != n || (n == 3 && cp < 0x800) || (n == 4 && cp < 0x10000) || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) cp = 0xfffd, n = 1;
  }
  if (cp > 0xffff) { if (o + 2 > limit) break; cp -= 0x10000; out[o++] = (uint16_t)(0xd800 + (cp >> 10)); out[o++] = (uint16_t)(0xdc00 + (cp & 1023)); }
  else out[o++] = (uint16_t)cp;
  p += n;
 }
 out[o] = 0;
}
extern int overlay_ime_available(void);
int ime_active(void) {
	pthread_mutex_lock(&ime_mu);
	const int active = ime.open && ime.interactive && ime.phase < 4;
	pthread_mutex_unlock(&ime_mu);
	return active;
}
int ime_view(ImeView *out) {
 if (!out) return 0;
 pthread_mutex_lock(&ime_mu); memset(out, 0, sizeof *out);
 if (ime.open && ime.interactive && !ime.response) { out->open = 1; out->seq = ime.seq; out->max_utf16 = ime_limit(); memcpy(out->text, ime.text, sizeof out->text); }
 pthread_mutex_unlock(&ime_mu); return out->open;
}
void ime_submit(unsigned seq, const char *utf8) {
 pthread_mutex_lock(&ime_mu);
 if (ime.open && ime.interactive && !ime.response && ime.seq == seq) { ime_from_utf8(utf8 ? utf8 : "", ime.result, ime_limit()); ime.response = 1; }
 pthread_mutex_unlock(&ime_mu);
}
void ime_cancel(unsigned seq) {
 pthread_mutex_lock(&ime_mu);
 if (ime.open && ime.interactive && !ime.response && ime.seq == seq) { memcpy(ime.result, ime.initial, sizeof ime.result); ime.response = 2; }
 pthread_mutex_unlock(&ime_mu);
}
static void ime_event(Cpu *c, uint32_t id, uint32_t caret) {
 memset(G(ime.ev), 0, 64); WR32(ime.ev, id);
 if (id == 1) { WR32(ime.ev + 12, caret); WR32(ime.ev + 16, ime.buf); }
 if (ime.handler) guest_call(c, ime.handler, ime.arg, ime.ev);
}
static void h_ime_open(Cpu *c) {
 if (!A0) { RET(0x80100702u); return; }
 pthread_mutex_lock(&ime_mu);
 /* A completed interactive request no longer owns input, even
  * if the guest defers Close until the next trip through the naming screen. */
 if (ime.open && (!ime.interactive || ime.phase < 4)) {
  pthread_mutex_unlock(&ime_mu); RET(0x80100701u); return;
 }
 ime.arg = RD32(A0 + 0x20); ime.handler = RD32(A0 + 0x24); ime.init = RD32(A0 + 0x2c); ime.maxlen = RD32(A0 + 0x30); ime.buf = RD32(A0 + 0x34);
 if (!ime.ev) ime.ev = guest_alloc(64, 16);
 const char *title = getenv("RECOMP_TITLE");
 ime.interactive = title && !strcmp(title, "PCSG00351") && !getenv("RECOMP_HEADLESS") && overlay_ime_available();
 ime.open = 1; ime.step = ime.response = ime.phase = 0; if (!++ime.seq) ++ime.seq;
 uint32_t n = 0, limit = ime_limit();
 if (ime.init) while (n < limit && RD16(ime.init + 2*n)) { ime.initial[n] = RD16(ime.init + 2*n); n++; }
 if (n && ime.initial[n-1] >= 0xd800 && ime.initial[n-1] <= 0xdbff) n--;
 ime.initial[n] = 0; ime_to_utf8(ime.initial, ime.text, sizeof ime.text);
 pthread_mutex_unlock(&ime_mu);
 fprintf(stderr, "    ime: keyboard opened (handler %#x, max %u chars)\n", ime.handler, ime.maxlen); RET(0);
}
static void h_ime_update(Cpu *c) {
 pthread_mutex_lock(&ime_mu);
 if (!ime.open) { pthread_mutex_unlock(&ime_mu); RET(0); return; }
 int interactive = ime.interactive, s = ime.step++, response = ime.response, phase = ime.phase;
 uint16_t result[IME_UNITS+1];
 if (interactive && response && phase == 0 && s >= 2) { memcpy(result, ime.result, sizeof result); ime.phase = 1; }
 else if (interactive && response && phase > 0 && phase < 3) ime.phase++;
 pthread_mutex_unlock(&ime_mu);
 if (!interactive) {
  if (s == 0) ime_event(c, 0, 0);
  else if (s == 2) {
   char shown[64]; uint32_t n = ime_fill(ime.init, ime.buf, ime.maxlen, shown);
   ime_event(c, 1, n); fprintf(stderr, "    ime: typed \"%s\"\n", shown);
  } else if (s == 10) { ime_event(c, 5, 0); fprintf(stderr, "    ime: Enter\n"); }
 } else if (s == 0) ime_event(c, 0, 0);
 else if (response && phase == 0 && s >= 2) {
  uint32_t n = 0; if (ime.buf) { while (result[n]) { WR16(ime.buf + 2*n, result[n]); n++; } WR16(ime.buf + 2*n, 0); }
  ime_event(c, 1, n);
 } else if (response && phase == 3) {
  pthread_mutex_lock(&ime_mu);
  ime.phase = 4;
  pthread_mutex_unlock(&ime_mu);
  ime_event(c, response == 2 ? 4 : 5, 0);
  fprintf(stderr, "    ime: name entry %s\n", response == 2 ? "canceled" : "confirmed");
 }
 RET(0);
}
static void h_ime_close(Cpu *c) { pthread_mutex_lock(&ime_mu); ime.open = 0; pthread_mutex_unlock(&ime_mu); RET(0); }
static void h_ime_dialog_status(Cpu *c) { RET((uint32_t)ime_state); }
static void h_ime_dialog_result(Cpu *c) { if (!A0) { RET(0x80020402u); return; } memset(G(A0), 0, 36); WR32(A0 + 4, 2); RET(0); }   /* result 0, button ENTER */
static void h_ime_dialog_term(Cpu *c) { ime_state = 0; RET(0); }
static void h_ime_dialog_abort(Cpu *c) { ime_state = 0; RET(0); }

const HleEntry hle_apputil[] = {
	{"sceImeDialogInit", h_ime_dialog_init}, {"sceImeDialogGetStatus", h_ime_dialog_status}, {"sceImeDialogGetResult", h_ime_dialog_result},
	{"sceImeDialogTerm", h_ime_dialog_term}, {"sceImeDialogAbort", h_ime_dialog_abort},
	{"sceImeOpen", h_ime_open}, {"sceImeUpdate", h_ime_update}, {"sceImeClose", h_ime_close},
	{"sceAppUtilSaveDataSlotSearch", h_save_slot_search}, {"sceAppUtilSaveDataMount", h_save_mount_other}, {"sceAppUtilSaveDataUmount", h_zero_ok},
	{"sceAppMgrAppParamGetString", h_app_param_string},
	{"sceAppMgrReceiveSystemEvent", h_receive_system_event},
	{"sceAppUtilSystemParamGetInt", h_system_param_int}, {"_sceAppMgrGetAppState", h_app_state}, {"sceSysmoduleIsLoaded", h_zero_ok},
	{"sceAppUtilSystemParamGetString", h_system_param_string},
	{"sceAppUtilInit", h_zero}, {"sceAppUtilShutdown", h_zero}, {"sceAppUtilDrmOpen", h_drm_open}, {"sceAppUtilDrmClose", h_zero},   /* (SceAppUtilDrmAddcontId *, mount point): the additional content's licence -- the host has no DRM, every add-on is licensed */   /* (SceAppUtilInitParam *, SceAppUtilBootParam *): nothing to set up */
	{"sceAppUtilReceiveAppEvent", h_receive_app_event},
	{"sceAppUtilAppEventParseLiveArea", h_app_event_parse}, {"sceAppUtilAppEventParseNearGift", h_app_event_parse},
	{"sceAppUtilAppEventParseNpInviteMessage", h_app_event_parse}, {"sceAppUtilAppEventParseNpBasicJoinablePresence", h_app_event_parse},
	{"sceAppUtilAppEventParseNpActivity", h_app_event_parse}, {"sceAppUtilAppEventParseNpAppDataMessage", h_app_event_parse},
	{"sceAppUtilAppEventParseSessionInvitation", h_app_event_parse}, {"sceAppUtilAppEventParseTeleport", h_app_event_parse},
	{"sceAppUtilAppEventParseGameCustomData", h_app_event_parse}, {"sceAppUtilAppEventParseWebBrowser", h_app_event_parse},
	{"sceKernelGetOpenPsId", h_open_psid},
	{"sceAppMgrSetNetworkDisconnectionWarningDialogState", h_zero},   /* the system's "network lost" dialog: never shown */
	/* power: always on mains, plenty of charge; the idle timers PowerTick resets don't exist */
	{"scePowerIsLowBattery", h_zero}, {"sceKernelPowerTick", h_zero}, {"scePowerSetConfigurationMode", h_zero},
	{"sceAvPlayerInit", h_avplayer_init}, {"sceAvPlayerAddSource", h_avplayer_add_source},
	{"sceAvPlayerIsActive", h_zero}, {"sceAvPlayerGetVideoData", h_avplayer_frame}, {"sceAvPlayerGetAudioData", h_avplayer_frame},
	{"sceAvPlayerStreamCount", h_zero}, {"sceAvPlayerGetStreamInfo", h_avplayer_no_stream}, {"sceAvPlayerEnableStream", h_avplayer_no_stream},
	{"sceAvPlayerStart", h_avplayer_no_stream}, {"sceAvPlayerJumpToTime", h_avplayer_no_stream}, {"sceAvPlayerCurrentTime", h_avplayer_time},
	{"sceAvPlayerClose", h_zero}, {"sceAvPlayerStop", h_zero}, {"sceAvPlayerPause", h_zero}, {"sceAvPlayerResume", h_zero},
	{"sceNpTrophySetupDialogInit", h_trophy_dlg_init},
	{"sceNpTrophySetupDialogGetStatus", h_trophy_dlg_status},
	{"sceNpTrophySetupDialogGetResult", h_dialog_result},
	{"sceNpTrophySetupDialogTerm", h_trophy_dlg_term},
	{"sceSaveDataDialogInit", h_save_dlg_init},
	{"sceSaveDataDialogGetStatus", h_save_dlg_status},
	{"sceSaveDataDialogGetResult", h_save_dlg_result},
	{"sceSaveDataDialogTerm", h_save_dlg_term}, {"sceSaveDataDialogContinue", h_save_dlg_continue}, {"sceSaveDataDialogGetSubStatus", h_save_dlg_substatus},
	{"sceSaveDataDialogFinish", h_save_dlg_finish}, {"sceSaveDataDialogSubClose", h_save_dlg_subclose}, {"sceSaveDataDialogAbort", h_save_dlg_abort},
	{"sceSaveDataDialogProgressBarInc", h_save_dlg_bar_inc}, {"sceSaveDataDialogProgressBarSetValue", h_save_dlg_bar_set},
	{"sceNetCheckDialogInit", h_net_dlg_init},
	{"sceNetCheckDialogGetStatus", h_net_dlg_status},
	{"sceNetCheckDialogGetResult", h_net_dlg_result},
	{"sceNetCheckDialogTerm", h_net_dlg_term},
	{"sceMsgDialogInit", h_msg_dlg_init},
	{"sceMsgDialogGetStatus", h_msg_dlg_status},
	{"sceMsgDialogGetResult", h_dialog_result},
	{"sceMsgDialogTerm", h_msg_dlg_term},
	{"SceCommonDialog_33626E2C", h_eula_dlg_init}, {"SceCommonDialog_B7D4C911", h_eula_dlg_status},
	{"SceCommonDialog_D1858A78", h_eula_dlg_result}, {"SceCommonDialog_BEBAEF25", h_eula_dlg_term}, {"SceCommonDialog_B55CF0E3", h_eula_dlg_term},
	{"sceCommonDialogUpdate", h_zero},
	{"sceAppMgrIsGameProgram", h_is_game},   /* 1: a game -- libfios2 picks its default file mode by it */
	{"sceAppUtilSaveDataSlotGetParam", h_save_slot_param}, {"sceAppUtilSaveDataSlotCreate", h_save_slot_create}, {"sceAppUtilSaveDataSlotDelete", h_save_slot_delete}, {"sceAppUtilSaveDataSlotSetParam", h_save_slot_set_param},
	{"sceAppUtilSaveDataDataSave", h_save_data_save},
	{"sceAppUtilSaveDataDataRemove", h_save_data_remove},
	{"sceNpTrophyCreateContext", h_trophy_create},
	{"sceNpTrophyCreateHandle", h_trophy_create},
	{0, 0},
};
