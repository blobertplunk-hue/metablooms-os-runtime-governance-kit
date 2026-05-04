#include <archive.h>
#include <archive_entry.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <sys/stat.h>
#include <errno.h>

static int unsafe_path(const char *p) {
    if (!p || !*p) return 1;
    if (p[0] == '/') return 1;
    if (strstr(p, "\\")) return 1;
    const char *s = p;
    while (*s) {
        while (*s == '/') s++;
        const char *e = strchr(s, '/');
        size_t n = e ? (size_t)(e - s) : strlen(s);
        if (n == 2 && s[0] == '.' && s[1] == '.') return 1;
        if (!e) break;
        s = e + 1;
    }
    return 0;
}

static void usage(void) {
    fprintf(stderr, "Usage: mb_archive_tool list|test <archive> | extract <archive> <dest>\n");
}

static int copy_data(struct archive *ar, struct archive *aw) {
    const void *buff; size_t size; la_int64_t offset;
    for (;;) {
        int r = archive_read_data_block(ar, &buff, &size, &offset);
        if (r == ARCHIVE_EOF) return ARCHIVE_OK;
        if (r < ARCHIVE_OK) return r;
        r = archive_write_data_block(aw, buff, size, offset);
        if (r < ARCHIVE_OK) return r;
    }
}

static struct archive* open_reader(const char *path) {
    struct archive *a = archive_read_new();
    archive_read_support_filter_all(a);
    archive_read_support_format_all(a);
    int r = archive_read_open_filename(a, path, 10240);
    if (r != ARCHIVE_OK) {
        fprintf(stderr, "open_error: %s\n", archive_error_string(a));
        archive_read_free(a);
        return NULL;
    }
    return a;
}

int main(int argc, char **argv) {
    if (argc < 3) { usage(); return 64; }
    const char *cmd = argv[1];
    const char *arc = argv[2];
    struct archive_entry *entry;
    int count = 0, skipped = 0;

    if (strcmp(cmd, "list") == 0 || strcmp(cmd, "test") == 0) {
        struct archive *a = open_reader(arc);
        if (!a) return 2;
        while (1) {
            int r = archive_read_next_header(a, &entry);
            if (r == ARCHIVE_EOF) break;
            if (r < ARCHIVE_OK) fprintf(stderr, "warn: %s\n", archive_error_string(a));
            if (r < ARCHIVE_WARN) { archive_read_free(a); return 3; }
            const char *p = archive_entry_pathname(entry);
            if (unsafe_path(p)) { fprintf(stderr, "unsafe_path: %s\n", p ? p : "(null)"); skipped++; archive_read_data_skip(a); continue; }
            count++;
            if (strcmp(cmd, "list") == 0) printf("%s\n", p);
            int rr = archive_read_data_skip(a);
            if (rr < ARCHIVE_WARN) { fprintf(stderr, "read_error: %s\n", archive_error_string(a)); archive_read_free(a); return 4; }
        }
        archive_read_free(a);
        fprintf(stderr, "{\"ok\":true,\"command\":\"%s\",\"entries\":%d,\"skipped_unsafe\":%d}\n", cmd, count, skipped);
        return skipped ? 10 : 0;
    }

    if (strcmp(cmd, "extract") == 0) {
        if (argc < 4) { usage(); return 64; }
        const char *dest = argv[3];
        if (!dest || !*dest || dest[0] != '/') { fprintf(stderr, "dest_must_be_absolute\n"); return 65; }
        mkdir(dest, 0775);
        struct archive *a = open_reader(arc);
        if (!a) return 2;
        struct archive *ext = archive_write_disk_new();
        archive_write_disk_set_options(ext, ARCHIVE_EXTRACT_TIME | ARCHIVE_EXTRACT_PERM | ARCHIVE_EXTRACT_SECURE_SYMLINKS | ARCHIVE_EXTRACT_SECURE_NODOTDOT | ARCHIVE_EXTRACT_SECURE_NOABSOLUTEPATHS);
        archive_write_disk_set_standard_lookup(ext);
        while (1) {
            int r = archive_read_next_header(a, &entry);
            if (r == ARCHIVE_EOF) break;
            if (r < ARCHIVE_OK) fprintf(stderr, "warn: %s\n", archive_error_string(a));
            if (r < ARCHIVE_WARN) { archive_read_free(a); archive_write_free(ext); return 3; }
            const char *p = archive_entry_pathname(entry);
            if (unsafe_path(p)) { fprintf(stderr, "unsafe_path: %s\n", p ? p : "(null)"); skipped++; archive_read_data_skip(a); continue; }
            size_t need = strlen(dest) + 1 + strlen(p) + 1;
            char *full = malloc(need);
            if (!full) { perror("malloc"); archive_read_free(a); archive_write_free(ext); return 70; }
            snprintf(full, need, "%s/%s", dest, p);
            archive_entry_set_pathname(entry, full);
            r = archive_write_header(ext, entry);
            if (r < ARCHIVE_OK) fprintf(stderr, "write_header_warn: %s\n", archive_error_string(ext));
            if (r < ARCHIVE_WARN) { free(full); archive_read_free(a); archive_write_free(ext); return 5; }
            if (archive_entry_size(entry) > 0) {
                r = copy_data(a, ext);
                if (r < ARCHIVE_WARN) { fprintf(stderr, "write_data_error: %s\n", archive_error_string(ext)); free(full); archive_read_free(a); archive_write_free(ext); return 6; }
            }
            r = archive_write_finish_entry(ext);
            free(full);
            if (r < ARCHIVE_WARN) { fprintf(stderr, "finish_entry_error: %s\n", archive_error_string(ext)); archive_read_free(a); archive_write_free(ext); return 7; }
            count++;
        }
        archive_read_free(a);
        archive_write_free(ext);
        fprintf(stderr, "{\"ok\":true,\"command\":\"extract\",\"entries\":%d,\"skipped_unsafe\":%d,\"dest\":\"%s\"}\n", count, skipped, dest);
        return skipped ? 10 : 0;
    }
    usage(); return 64;
}
