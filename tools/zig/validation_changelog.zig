//! Native port of scripts/docs/check_changelog_style.py and the reachable shared
//! release-section extractor, pinned by changelog-component-r1/oracle-pins.json.
//! No subprocess, locale, network, or runtime Python dependency. Unicode property
//! qualification is CPython 3.11.15 / Unicode 14.0.0; no all-version claim.
const std = @import("std");
const unicode = @import("validation_unicode14.zig");
const A = std.mem.Allocator;
const Line = struct { number: usize, text: []const u8 };
const Heading = struct { level: usize, text: []const u8, number: usize };
const Block = struct { number: usize, lines: std.ArrayList([]const u8) = .empty };
const Entry = struct {
    section: []const u8,
    number: usize,
    lines: std.ArrayList([]const u8) = .empty,
    nested: std.ArrayList(Block) = .empty,
    numbered: std.ArrayList(Line) = .empty,
    indent: ?usize = null,
    headline: ?[]const u8 = null,
    fn add(self: *Entry, a: A, line: Line) !void {
        try self.numbered.append(a, line);
        const nested = nestedIndent(line.text);
        if (nested != null and (self.indent == null or nested.? <= self.indent.?)) {
            self.indent = nested;
            var block: Block = .{ .number = line.number };
            try block.lines.append(a, line.text);
            try self.nested.append(a, block);
        } else if (self.nested.items.len > 0 and (nested != null or indentation(line.text) >= 2)) {
            try self.nested.items[self.nested.items.len - 1].lines.append(a, line.text);
        } else try self.lines.append(a, line.text);
    }
};
const Orphan = struct { section: []const u8, line: Line };
const Foreign = struct { section: ?[]const u8, line: Line };
const Parsed = struct {
    preamble: std.ArrayList(Line) = .empty,
    headings: std.ArrayList(Heading) = .empty,
    entries: std.ArrayList(Entry) = .empty,
    orphans: std.ArrayList(Orphan) = .empty,
    foreign: std.ArrayList(Foreign) = .empty,
};
pub const Finding = struct { severity: []const u8 = "error", rule: []const u8, path: []const u8, line: usize, where: []const u8, fix: []const u8 };
const sections = [_][]const u8{ "Breaking", "Upgrade Notes", "Added", "Changed", "Fixed", "Internal" };
const order_text = "Breaking, Upgrade Notes, Added, Changed, Fixed, Internal";
fn eq(a: []const u8, b: []const u8) bool {
    return std.mem.eql(u8, a, b);
}
fn starts(s: []const u8, prefix: []const u8) bool {
    return std.mem.startsWith(u8, s, prefix);
}
fn has(s: []const u8, part: []const u8) bool {
    return std.mem.indexOf(u8, s, part) != null;
}
fn sequenceWidth(byte: u8) usize {
    if (byte < 0x80) return 1;
    if (byte >= 0xc2 and byte <= 0xdf) return 2;
    if (byte >= 0xe0 and byte <= 0xef) return 3;
    if (byte >= 0xf0 and byte <= 0xf4) return 4;
    return 0;
}
// Callers traverse already validated UTF-8; no locale-dependent decoding.
fn next(s: []const u8, i: usize) usize {
    return i + sequenceWidth(s[i]);
}
fn cp(s: []const u8, i: usize) u21 {
    const width = sequenceWidth(s[i]);
    if (width == 1) return s[i];
    var value: u21 = s[i] & (@as(u8, 0x7f) >> @intCast(width));
    for (s[i + 1 .. i + width]) |byte| value = (value << 6) | (byte & 0x3f);
    return value;
}
fn previous(s: []const u8, i: usize) usize {
    var j = i - 1;
    while (s[j] & 0xc0 == 0x80) j = j - 1;
    return j;
}
fn space(s: []const u8, i: usize) bool {
    return unicode.properties(cp(s, i)) & 4 != 0;
}
fn word(s: []const u8, i: usize) bool {
    return unicode.properties(cp(s, i)) & 1 != 0;
}
fn decimal(s: []const u8, i: usize) bool {
    return unicode.properties(cp(s, i)) & 2 != 0;
}
fn whitespace(s: []const u8, i: usize) usize {
    var j = i;
    while (j < s.len and space(s, j)) j = next(s, j);
    return j;
}
fn left(s: []const u8) []const u8 {
    return s[whitespace(s, 0)..];
}
fn right(s: []const u8) []const u8 {
    var end = s.len;
    while (end > 0 and space(s, previous(s, end))) end = previous(s, end);
    return s[0..end];
}
fn trim(s: []const u8) []const u8 {
    return left(right(s));
}
fn length(s: []const u8) usize {
    var count: usize = 0;
    for (s) |byte| {
        if (byte & 0xc0 != 0x80) count += 1;
    }
    return count;
}
fn shorten(a: A, s: []const u8, max: usize) ![]const u8 {
    if (length(s) <= max) return s;
    var i: usize = 0;
    for (0..max - 1) |_| i = next(s, i);
    return std.mem.concat(a, u8, &.{ s[0..i], "…" });
}
fn indentation(s: []const u8) usize {
    return length(s[0..whitespace(s, 0)]);
}
fn nestedIndent(s: []const u8) ?usize {
    const i = whitespace(s, 0);
    if (length(s[0..i]) >= 2 and starts(s[i..], "- ")) return length(s[0..i]);
    return null;
}
fn linesOf(a: A, text: []const u8) ![]Line {
    var lines: std.ArrayList(Line) = .empty;
    var start: usize = 0;
    var i: usize = 0;
    while (i < text.len) {
        const c = cp(text, i);
        const end = next(text, i);
        if (c == 10 or c == 13 or c == 11 or c == 12 or (c >= 28 and c <= 30) or c == 0x85 or c == 0x2028 or c == 0x2029) {
            try lines.append(a, .{ .number = lines.items.len + 1, .text = text[start..i] });
            i = end;
            if (c == 13 and i < text.len and text[i] == 10) i += 1;
            start = i;
        } else i = end;
    }
    if (start < text.len) try lines.append(a, .{ .number = lines.items.len + 1, .text = text[start..] });
    return lines.items;
}
fn insensitive(s: []const u8, at: usize, literal: []const u8) ?usize {
    var i = at;
    for (literal) |wanted| {
        if (i == s.len) return null;
        var value = cp(s, i);
        if (value >= 65 and value <= 90) value += 32;
        if (value == 0x17f) value = 's'; // Python Unicode IGNORECASE for ASCII s.
        if (value != wanted) return null;
        i = next(s, i);
    }
    return i;
}
fn digits(s: []const u8, at: usize) ?usize {
    var i = at;
    while (i < s.len and decimal(s, i)) i = next(s, i);
    if (i == at) return null;
    return i;
}
fn version(s: []const u8, at: usize) ?usize {
    var i = digits(s, at) orelse return null;
    for (0..2) |_| {
        if (i == s.len or s[i] != '.') return null;
        i = digits(s, i + 1) orelse return null;
    }
    if (i < s.len and s[i] == '.') {
        if (digits(s, i + 1)) |end| i = end;
    }
    for ([_][]const u8{ "alpha", "beta", "rc", "a", "b" }) |stage| {
        if (insensitive(s, i, stage)) |end| {
            if (digits(s, end)) |last| return last;
            if (eq(stage, "alpha") or eq(stage, "beta")) return end;
        }
    }
    return i;
}
fn closing(s: []const u8, at: usize) usize {
    var i = whitespace(s, at);
    if (i < s.len and s[i] == ']') i += 1;
    return whitespace(s, i);
}
fn tail(s: []const u8, at: usize) bool {
    const i = closing(s, at);
    return i == s.len or s[i] == '-';
}
// null = not a release heading, false = finalized, true = Unreleased.
fn releaseHeading(s: []const u8) ?bool {
    if (!starts(s, "##")) return null;
    var i = whitespace(s, 2);
    if (i < s.len and s[i] == '[') i = whitespace(s, i + 1);
    if (insensitive(s, i, "unreleased")) |end| {
        var j = closing(s, end);
        if (tail(s, j)) return true;
        if (j < s.len and s[j] == '-') j = whitespace(s, j + 1);
        if (version(s, j)) |last| {
            if (tail(s, last)) return true;
        }
    }
    if (version(s, i)) |end| {
        const j = closing(s, end);
        if (j < s.len and s[j] == '-') {
            if (insensitive(s, whitespace(s, j + 1), "unreleased")) |last| {
                if (tail(s, last)) return true;
            }
        }
        if (tail(s, j)) return false;
    }
    return null;
}
fn fence(s: []const u8) ?[]const u8 {
    const t = left(s);
    if (starts(t, "```")) return "```";
    if (starts(t, "~~~")) return "~~~";
    return null;
}
fn unreleased(lines: []const Line) ?[]const Line {
    var begin: ?usize = null;
    var open: ?[]const u8 = null;
    for (lines, 0..) |line, index| {
        const marker = fence(line.text);
        if (marker != null and (open == null or eq(open.?, marker.?))) {
            if (open == null) {
                open = marker;
            } else open = null;
        } else if (open == null and starts(line.text, "##")) {
            if (releaseHeading(line.text)) |pending| {
                if (begin == null and pending) {
                    begin = index + 1;
                    continue;
                }
                if (begin != null) return lines[begin.?..index];
            }
        }
    }
    if (begin) |first| return lines[first..];
    return null;
}
fn heading(s: []const u8, number: usize) ?Heading {
    var i: usize = 0;
    while (i < s.len and s[i] == '#') i += 1;
    if ((i != 3 and i != 4) or i == s.len or !space(s, i)) return null;
    return .{ .level = i, .text = trim(s[i..]), .number = number };
}
fn headline(s: []const u8) ?struct { text: []const u8, end: usize } {
    if (!starts(s, "- **")) return null;
    if (s.len <= 4) return null;
    // .+? requires at least one character, even when stars overlap.
    const at = std.mem.indexOf(u8, s[next(s, 4)..], "**") orelse return null;
    const end = next(s, 4) + at;
    return .{ .text = s[4..end], .end = end + 2 };
}
fn closeEntry(a: A, parsed: *Parsed, draft: *?Entry) !void {
    if (draft.*) |value| {
        var entry = value;
        const joined = try std.mem.join(a, "\n", entry.lines.items);
        if (headline(joined)) |h| entry.headline = h.text;
        try parsed.entries.append(a, entry);
        draft.* = null;
    }
}
fn attach(a: A, parsed: *Parsed, draft: *?Entry, section: ?[]const u8, line: Line) !void {
    if (draft.*) |*entry| {
        try entry.add(a, line);
    } else if (section) |name| {
        try parsed.orphans.append(a, .{ .section = name, .line = line });
    } else try parsed.preamble.append(a, line);
}
fn parseSection(a: A, lines: []const Line) !Parsed {
    var parsed: Parsed = .{};
    var section: ?[]const u8 = null;
    var draft: ?Entry = null;
    var in_fence = false;
    for (lines) |line| {
        if (starts(left(line.text), "```")) {
            in_fence = !in_fence;
            try attach(a, &parsed, &draft, section, line);
        } else if (in_fence) {
            try attach(a, &parsed, &draft, section, line);
        } else if (heading(line.text, line.number)) |h| {
            try closeEntry(a, &parsed, &draft);
            try parsed.headings.append(a, h);
            if (h.level == 3) section = h.text;
        } else if (starts(line.text, "- ")) {
            try closeEntry(a, &parsed, &draft);
            if (section) |name| {
                var entry: Entry = .{ .section = name, .number = line.number };
                try entry.lines.append(a, line.text);
                try entry.numbered.append(a, line);
                draft = entry;
            } else try parsed.preamble.append(a, line);
        } else if (line.text.len > 1 and (line.text[0] == '*' or line.text[0] == '+') and space(line.text, 1)) {
            try parsed.foreign.append(a, .{ .section = section, .line = line });
            try attach(a, &parsed, &draft, section, line);
        } else if (trim(line.text).len > 0) {
            try attach(a, &parsed, &draft, section, line);
        } else if (section == null) try parsed.preamble.append(a, line);
    }
    try closeEntry(a, &parsed, &draft);
    return parsed;
}
fn finding(a: A, findings: *std.ArrayList(Finding), path: []const u8, number: usize, rule: []const u8, where: []const u8, fix: []const u8) !void {
    try findings.append(a, .{ .rule = rule, .path = path, .line = number, .where = where, .fix = fix });
}
fn rank(s: []const u8) ?usize {
    for (sections, 0..) |name, i| if (eq(s, name)) return i;
    return null;
}
fn headingChecks(a: A, parsed: Parsed, path: []const u8, findings: *std.ArrayList(Finding)) !void {
    var seen: [6]?usize = @splat(null);
    var subsections = std.StringHashMap(usize).init(a);
    var parent: ?[]const u8 = null;
    for (parsed.headings.items) |h| {
        const hashes = try a.alloc(u8, h.level);
        for (hashes) |*value| value.* = '#';
        const where = try std.fmt.allocPrint(a, "[{s}] {s} {s}", .{ h.text, hashes, h.text });
        if (h.level == 3) {
            parent = h.text;
            subsections.clearRetainingCapacity();
            if (rank(h.text)) |r| {
                if (seen[r]) |number| {
                    try finding(a, findings, path, h.number, "heading-duplicate", where, try std.fmt.allocPrint(a, "Merge this `### {s}` into the earlier one at line {d}.", .{ h.text, number }));
                } else {
                    seen[r] = h.number;
                    for (r + 1..6) |later| {
                        if (seen[later] != null) {
                            try finding(a, findings, path, h.number, "heading-order", where, try std.fmt.allocPrint(a, "Move `### {s}` above `### {s}`; required order: " ++ order_text ++ ".", .{ h.text, sections[later] }));
                            break;
                        }
                    }
                }
            } else try finding(a, findings, path, h.number, "heading-unknown", where, "Use one of: " ++ order_text ++ ".");
        } else if (parent == null or !eq(parent.?, "Fixed")) {
            try finding(a, findings, path, h.number, "subheading-placement", where, "Use `####` only under `### Fixed`; remove it or move the entries into `### Fixed`.");
        } else if (subsections.get(h.text)) |number| {
            try finding(a, findings, path, h.number, "heading-duplicate", where, try std.fmt.allocPrint(a, "Merge this `#### {s}` into the earlier one at line {d}.", .{ h.text, number }));
        } else try subsections.put(h.text, h.number);
    }
}
fn entryWhere(a: A, entry: Entry) ![]const u8 {
    var shown = trim(entry.lines.items[0][2..]);
    if (entry.headline) |value| shown = value;
    return std.fmt.allocPrint(a, "[{s}] {s}", .{ entry.section, try shorten(a, shown, 60) });
}
fn stripCode(a: A, text: []const u8) ![]const u8 {
    var result: std.ArrayList(u8) = .empty;
    var i: usize = 0;
    while (i < text.len) {
        if (text[i] == '`') {
            if (std.mem.indexOfScalar(u8, text[i + 1 ..], '`')) |offset| {
                const end = i + offset + 2;
                while (i < end) {
                    if (text[i] == '\n') {
                        try result.append(a, '\n');
                    } else try result.append(a, ' ');
                    i = next(text, i);
                }
                continue;
            }
        }
        const end = next(text, i);
        try result.appendSlice(a, text[i..end]);
        i = end;
    }
    return result.items;
}
fn boundary(s: []const u8, i: usize) bool {
    if (i == 0 or i == s.len) return true;
    return word(s, previous(s, i)) != word(s, i);
}
fn issue(s: []const u8, i: usize) ?usize {
    if (i == s.len or s[i] != '#') return null;
    return digits(s, i + 1);
}
fn reference(s: []const u8, i: usize) ?usize {
    if (issue(s, i)) |end| return end;
    var j = i;
    while (j < s.len and (word(s, j) or s[j] == '.' or s[j] == '-')) j = next(s, j);
    if (j == i or j == s.len or s[j] != '/') return null;
    const begin = j + 1;
    j = begin;
    while (j < s.len and (word(s, j) or s[j] == '.' or s[j] == '-')) j = next(s, j);
    if (j == begin) return null;
    return issue(s, j);
}
fn refsEnd(s: []const u8) ?usize {
    var i = whitespace(s, 0);
    if (i == s.len or s[i] != '(') return null;
    i = reference(s, whitespace(s, i + 1)) orelse return null;
    while (true) {
        const j = whitespace(s, i);
        if (j < s.len and s[j] == ',') {
            i = reference(s, whitespace(s, j + 1)) orelse return null;
        } else {
            if (j < s.len and s[j] == ')') return j + 1;
            return null;
        }
    }
}
fn body(a: A, entry: Entry) ![]const u8 {
    const strings = try a.alloc([]const u8, entry.lines.items.len);
    for (entry.lines.items, 0..) |line, i| strings[i] = trim(line);
    var text = try std.mem.join(a, " ", strings);
    if (headline(text)) |h| text = text[h.end..];
    if (refsEnd(text)) |end| text = text[end..];
    var i: usize = 0;
    while (i < text.len and (text[i] == '.' or text[i] == ' ' or text[i] == '\t')) i += 1;
    return trim(text[i..]);
}
fn sentenceCount(text: []const u8) usize {
    const s = trim(text);
    if (s.len == 0) return 0;
    var count: usize = 1;
    var i: usize = 0;
    while (i < s.len) {
        const end = next(s, i);
        if ((s[i] == '.' or s[i] == '!' or s[i] == '?') and end < s.len and space(s, end)) {
            i = whitespace(s, end);
            if (i < s.len) count += 1;
        } else i = end;
    }
    return count;
}
fn fullText(a: A, entry: Entry) ![]const u8 {
    var list: std.ArrayList([]const u8) = .empty;
    try list.appendSlice(a, entry.lines.items);
    for (entry.nested.items) |block| try list.appendSlice(a, block.lines.items);
    return std.mem.join(a, "\n", list.items);
}
fn lengthCheck(a: A, findings: *std.ArrayList(Finding), path: []const u8, number: usize, where: []const u8, raw: []const []const u8) !void {
    const size = length(try std.mem.join(a, "\n", raw));
    if (size > 1200) {
        try finding(a, findings, path, number, "length", where, try std.fmt.allocPrint(a, "Entry is {d} characters (limit 1,200); split it or move detail to the docs.", .{size}));
    } else if (size > 900) try findings.append(a, .{ .severity = "warning", .rule = "length-warning", .path = path, .line = number, .where = where, .fix = try std.fmt.allocPrint(a, "Entry is {d} characters; aim for 900 or fewer.", .{size}) });
}
fn entryChecks(a: A, entry: Entry, path: []const u8, findings: *std.ArrayList(Finding)) !void {
    const where = try entryWhere(a, entry);
    const section_rank = rank(entry.section);
    if (section_rank != null and section_rank.? < 5 and entry.headline == null) try finding(a, findings, path, entry.number, "headline-missing", where, "Start the entry with a bold headline: `- **What changed** (#1234).`");
    if (entry.headline) |bold| {
        const stripped = try stripCode(a, bold);
        var refs: std.ArrayList([]const u8) = .empty;
        var i: usize = 0;
        while (i < stripped.len) {
            if (issue(stripped, i)) |end| {
                try refs.append(a, stripped[i..end]);
                i = end;
            } else i = next(stripped, i);
        }
        if (refs.items.len > 0) {
            const group = try std.mem.join(a, ", ", refs.items);
            try finding(a, findings, path, entry.number, "refs-in-bold", where, try std.fmt.allocPrint(a, "Move `({s})` out of the bold headline: `- **Headline** ({s}).`", .{ group, group }));
        }
    }
    if (eq(entry.section, "Breaking") or eq(entry.section, "Changed") or eq(entry.section, "Fixed")) {
        const full = try fullText(a, entry);
        const prose = try body(a, entry);
        if (!has(full, "**Before:**") and !(has(full, "**Why:**") and has(full, "**After:**")) and (sentenceCount(try stripCode(a, prose)) > 2 or length(prose) > 300)) try finding(a, findings, path, entry.number, "contrast-missing", where, "Add a `**Before:**` sentence describing the old behavior (or shorten the body to at most 2 sentences / 300 characters).");
    }
    if (eq(entry.section, "Internal") and (entry.lines.items.len != 1 or entry.nested.items.len > 0 or has(try std.mem.join(a, "\n", entry.lines.items), "**Before:**"))) try finding(a, findings, path, entry.number, "internal-shape", where, "Keep Internal entries to one line; move user-visible detail to Changed or Fixed.");
    try lengthCheck(a, findings, path, entry.number, where, entry.lines.items);
    for (entry.nested.items) |block| {
        var first = trim(block.lines.items[0]);
        if (starts(first, "- ")) first = first[2..];
        try lengthCheck(a, findings, path, block.number, try std.fmt.allocPrint(a, "{s} > {s}", .{ where, try shorten(a, first, 40) }), block.lines.items);
    }
}
const names = [_][]const u8{ "boilerplate", "requirement id", "ULID", "evidence path", "planning ref", "all-caps", "retired command" };
const fixes = [_][]const u8{
    "Delete the boilerplate; the section heading already says it is a fix.",
    "",
    "Remove the mission/event ULID; link the issue instead.",
    "Remove the local evidence path; it is not reachable by users.",
    "Remove the private planning-repo reference.",
    "Write `default`/`refuses`/`fails` in lowercase prose, or put the literal CLI token in backticks.",
    "Use `spec-kitty consolidate`; `spec-kitty merge` was renamed (only the rename entry may name it).",
};
fn requirement(s: []const u8, i: usize) ?usize {
    if (!boundary(s, i)) return null;
    for ([_][]const u8{ "FR-", "NFR-", "SC-", "C-", "D-" }) |prefix| {
        if (!starts(s[i..], prefix)) continue;
        var end = digits(s, i + prefix.len) orelse continue;
        if (end < s.len and s[end] >= 'a' and s[end] <= 'z') end += 1;
        if (end < s.len and s[end] == '.') {
            if (digits(s, end + 1)) |last| {
                if (boundary(s, last)) return last;
            }
        }
        if (boundary(s, end)) return end;
        // Optional [a-z] may backtrack when the following word blocks it.
        if (end > i and s[end - 1] >= 'a' and s[end - 1] <= 'z' and boundary(s, end - 1)) return end - 1;
    }
    return null;
}
fn tokenMatch(s: []const u8, i: usize, kind: usize) ?usize {
    if (kind == 0 and starts(s[i..], "Bug-fix")) {
        var j = whitespace(s, i + 7);
        if (j == s.len) return null;
        const value = cp(s, j);
        if (value != ';' and value != '-' and value != 0x2014 and value != 0x2013) return null;
        j = whitespace(s, next(s, j));
        if (starts(s[j..], "no CLI version bump")) return j + 19;
    }
    if (kind == 1) return requirement(s, i);
    if (kind == 2 and boundary(s, i) and s[i] >= '0' and s[i] <= '7' and s.len - i >= 26) {
        var valid = true;
        for (s[i + 1 .. i + 26]) |c| valid = valid and std.mem.indexOfScalar(u8, "0123456789ABCDEFGHJKMNPQRSTVWXYZ", c) != null;
        if (valid and boundary(s, i + 26)) return i + 26;
    }
    if (kind == 3 and starts(s[i..], ".kittify/evidence/")) return i + 18;
    if (kind == 4 and starts(s[i..], "planning#")) return i + 9;
    if (kind == 5 and boundary(s, i)) {
        for ([_][]const u8{ "DEFAULT", "REFUSE", "FAIL" }) |literal| {
            if (starts(s[i..], literal) and boundary(s, i + literal.len)) return i + literal.len;
        }
    }
    if (kind == 6 and starts(s[i..], "spec-kitty merge")) {
        const end = i + 16;
        if (end == s.len or (s[end] != '-' and !word(s, end))) return end;
    }
    return null;
}
fn scanUnit(a: A, findings: *std.ArrayList(Finding), path: []const u8, where: []const u8, lines: []const Line) !void {
    const strings = try a.alloc([]const u8, lines.len);
    for (lines, 0..) |line, i| strings[i] = line.text;
    const text = try std.mem.join(a, "\n", strings);
    const stripped = try stripCode(a, text);
    var seen = std.StringHashMap(void).init(a);
    for (0..7) |kind| {
        if (kind == 6 and has(text, "spec-kitty consolidate")) continue;
        var searched: []const u8 = text;
        if (kind == 1 or kind == 5) searched = stripped;
        var i: usize = 0;
        var line_index: usize = 0;
        while (i < searched.len) {
            if (tokenMatch(searched, i, kind)) |end| {
                const matched = searched[i..end];
                const number = lines[line_index].number;
                const key = try std.fmt.allocPrint(a, "{d}:{d}:{s}", .{ kind, number, matched });
                if (!seen.contains(key)) {
                    try seen.put(key, {});
                    var fix = fixes[kind];
                    if (kind == 1) fix = try std.fmt.allocPrint(a, "Describe the behavior instead of citing internal requirement `{s}`; put an ID in backticks only when quoting CLI output.", .{matched});
                    try finding(a, findings, path, number, "banned-token", try std.fmt.allocPrint(a, "{s} (token: {s})", .{ where, matched }), fix);
                }
                for (searched[i..end]) |c| if (c == '\n') {
                    line_index += 1;
                };
                i = end;
            } else {
                if (searched[i] == '\n') line_index += 1;
                i = next(searched, i);
            }
        }
    }
}
fn unitChecks(a: A, parsed: Parsed, path: []const u8, findings: *std.ArrayList(Finding)) !void {
    var start: usize = 0;
    for (0..parsed.preamble.items.len + 1) |i| {
        if (i == parsed.preamble.items.len or trim(parsed.preamble.items[i].text).len == 0) {
            if (i > start) {
                try scanUnit(a, findings, path, try std.fmt.allocPrint(a, "[preamble] {s}", .{try shorten(a, trim(parsed.preamble.items[start].text), 60)}), parsed.preamble.items[start..i]);
            }
            start = i + 1;
        }
    }
    start = 0;
    while (start < parsed.orphans.items.len) {
        var end = start + 1;
        while (end < parsed.orphans.items.len and eq(parsed.orphans.items[end].section, parsed.orphans.items[start].section) and parsed.orphans.items[end].line.number == parsed.orphans.items[end - 1].line.number + 1) end += 1;
        const lines = try a.alloc(Line, end - start);
        for (parsed.orphans.items[start..end], 0..) |orphan, i| lines[i] = orphan.line;
        try scanUnit(a, findings, path, try std.fmt.allocPrint(a, "[{s}] {s}", .{ parsed.orphans.items[start].section, try shorten(a, trim(lines[0].text), 60) }), lines);
        start = end;
    }
    for (parsed.entries.items) |entry| try scanUnit(a, findings, path, try entryWhere(a, entry), entry.numbered.items);
    for (parsed.foreign.items) |bullet| {
        var name: []const u8 = "preamble";
        if (bullet.section) |value| {
            if (value.len > 0) name = value;
        }
        try finding(a, findings, path, bullet.line.number, "bullet-marker", try std.fmt.allocPrint(a, "[{s}] {s}", .{ name, try shorten(a, trim(bullet.line.text), 60) }), "Use `- ` for changelog entries.");
    }
}
fn findingLess(_: void, lhs: Finding, rhs: Finding) bool {
    for ([_][2][]const u8{.{ lhs.path, rhs.path }}) |pair| {
        const order = std.mem.order(u8, pair[0], pair[1]);
        if (order != .eq) return order == .lt;
    }
    if (lhs.line != rhs.line) return lhs.line < rhs.line;
    for ([_][2][]const u8{ .{ lhs.rule, rhs.rule }, .{ lhs.where, rhs.where }, .{ lhs.fix, rhs.fix } }) |pair| {
        const order = std.mem.order(u8, pair[0], pair[1]);
        if (order != .eq) return order == .lt;
    }
    return false;
}
pub fn check(a: A, text: []const u8, path: []const u8) !?[]Finding {
    if (!std.unicode.utf8ValidateSlice(text)) return error.InvalidUtf8;
    const section = unreleased(try linesOf(a, text)) orelse return null;
    const parsed = try parseSection(a, section);
    var findings: std.ArrayList(Finding) = .empty;
    try headingChecks(a, parsed, path, &findings);
    try unitChecks(a, parsed, path, &findings);
    for (parsed.entries.items) |entry| try entryChecks(a, entry, path, &findings);
    std.mem.sort(Finding, findings.items, {}, findingLess);
    return findings.items;
}

const program = "python -m scripts.docs.check_changelog_style";
const description = "Check the changelog's [Unreleased] section against the house style.";
const changelog_help = "changelog file to check; a relative path resolves against the repository root (default: docs/changelog/CHANGELOG.md)";
fn asciiInteger(raw: []const u8) bool {
    if (raw.len == 0) return false;
    var first: usize = 0;
    if (raw[0] == '+' or raw[0] == '-') first = 1;
    if (first == raw.len) return false;
    for (raw[first..], first..) |byte, index| {
        if (byte == '_') {
            // Python permits exactly one underscore between decimal digits.
            if (index == first or index + 1 == raw.len) return false;
            if (raw[index - 1] < '0' or raw[index - 1] > '9' or raw[index + 1] < '0' or raw[index + 1] > '9') return false;
        } else if (byte < '0' or byte > '9') return false;
    }
    return true;
}
fn formatterWidth(init: std.process.Init) !usize {
    var columns: i64 = 0;
    if (init.environ_map.get("COLUMNS")) |raw| {
        const integer = std.mem.trim(u8, raw, " \t\n\r\x0b\x0c");
        if (!asciiInteger(integer)) return terminalWidth();
        columns = std.fmt.parseInt(i64, integer, 10) catch return terminalWidth();
    }
    if (columns <= 0) return terminalWidth();
    if (columns < 3) return 0;
    return @intCast(columns - 2);
}
fn terminalWidth() usize {
    var size: std.c.winsize = .{ .row = 0, .col = 0, .xpixel = 0, .ypixel = 0 };
    if (std.c.ioctl(1, std.c.T.IOCGWINSZ, &size) == 0 and size.col > 2) return size.col - 2;
    return 78;
}
fn padding(a: A, output: *std.ArrayList(u8), count: usize) !void {
    for (0..count) |_| try output.append(a, ' ');
}
fn usageText(a: A, width: usize) ![]const u8 {
    const full = "usage: " ++ program ++ " [-h] [--changelog CHANGELOG]\n";
    if (full.len - 1 <= width) return full;
    var output: std.ArrayList(u8) = .empty;
    try output.appendSlice(a, "usage: " ++ program);
    var indent: usize = 7;
    var current: usize = 7 + program.len;
    if (current <= width * 3 / 4) {
        indent = current + 1;
    } else {
        try output.append(a, '\n');
        try padding(a, &output, indent);
        current = indent;
    }
    for ([_][]const u8{ "[-h]", "[--changelog CHANGELOG]" }) |part| {
        if (current > indent and current + 1 + part.len > width) {
            try output.append(a, '\n');
            try padding(a, &output, indent);
            current = indent;
        }
        if (current != indent) {
            try output.append(a, ' ');
            current += 1;
        }
        try output.appendSlice(a, part);
        current += part.len;
    }
    try output.append(a, '\n');
    return output.items;
}
fn wrapped(a: A, text: []const u8, width: usize) ![][]const u8 {
    var lines: std.ArrayList([]const u8) = .empty;
    var line: std.ArrayList(u8) = .empty;
    var words = std.mem.tokenizeScalar(u8, text, ' ');
    while (words.next()) |original| {
        var word_text = original;
        if (word_text.len > width and line.items.len > 0) {
            if (line.items.len + 1 < width) {
                try line.append(a, ' ');
                const taken = width - line.items.len;
                try line.appendSlice(a, word_text[0..taken]);
                word_text = word_text[taken..];
            }
            try lines.append(a, try line.toOwnedSlice(a));
        } else if (line.items.len > 0 and line.items.len + 1 + word_text.len > width) {
            try lines.append(a, try line.toOwnedSlice(a));
        }
        while (word_text.len > width) {
            try lines.append(a, word_text[0..width]);
            word_text = word_text[width..];
        }
        if (line.items.len > 0) try line.append(a, ' ');
        try line.appendSlice(a, word_text);
    }
    if (line.items.len > 0) try lines.append(a, try line.toOwnedSlice(a));
    return lines.items;
}
fn helpText(a: A, width: usize) ![]const u8 {
    var output: std.ArrayList(u8) = .empty;
    try output.appendSlice(a, try usageText(a, width));
    try output.append(a, '\n');
    for (try wrapped(a, description, @max(width, 11))) |line| {
        try output.appendSlice(a, line);
        try output.append(a, '\n');
    }
    try output.appendSlice(a, "\noptions:\n");
    var position: usize = 4;
    if (width > 24) position = @min(24, width - 20);
    var help_width: usize = 11;
    if (width > position) help_width = @max(width - position, 11);
    for ([_][2][]const u8{ .{ "-h, --help", "show this help message and exit" }, .{ "--changelog CHANGELOG", changelog_help } }) |action| {
        try output.appendSlice(a, "  ");
        try output.appendSlice(a, action[0]);
        var first_indent = position;
        if (position >= action[0].len + 4) {
            try padding(a, &output, position - action[0].len - 2);
            first_indent = 0;
        } else try output.append(a, '\n');
        for (try wrapped(a, action[1], help_width), 0..) |line, index| {
            var indent = position;
            if (index == 0) indent = first_indent;
            try padding(a, &output, indent);
            try output.appendSlice(a, line);
            try output.append(a, '\n');
        }
    }
    return output.items;
}
const Request = struct { repository_root: []const u8, argv: []const []const u8 };
fn emit(init: std.process.Init, bytes: []const u8) !void {
    try std.Io.File.stdout().writeStreamingAll(init.io, bytes);
}
fn argError(init: std.process.Init, message: []const u8) !u8 {
    try std.Io.File.stderr().writeStreamingAll(init.io, try std.fmt.allocPrint(init.arena.allocator(), "{s}" ++ program ++ ": error: {s}\n", .{ try usageText(init.arena.allocator(), try formatterWidth(init)), message }));
    return 2;
}
fn validPath(path: []const u8) bool {
    return path.len > 0 and std.mem.indexOfScalar(u8, path, 0) == null and std.unicode.utf8ValidateSlice(path);
}
fn normalizePath(a: A, path: []const u8) ![]const u8 {
    var parts: std.ArrayList([]const u8) = .empty;
    var iterator = std.mem.splitScalar(u8, path, '/');
    while (iterator.next()) |part| {
        if (part.len > 0 and !eq(part, ".")) try parts.append(a, part);
    }
    const joined = try std.mem.join(a, "/", parts.items);
    var prefix: []const u8 = "";
    if (starts(path, "/")) prefix = "/";
    if (starts(path, "//") and !starts(path, "///")) prefix = "//";
    if (prefix.len == 0 and joined.len == 0) return ".";
    return std.mem.concat(a, u8, &.{ prefix, joined });
}
fn pathRepr(a: A, path: []const u8) ![]const u8 {
    var quote: u8 = '\'';
    if (std.mem.indexOfScalar(u8, path, '\'') != null and std.mem.indexOfScalar(u8, path, '"') == null) quote = '"';
    var output: std.ArrayList(u8) = .empty;
    try output.append(a, quote);
    var i: usize = 0;
    while (i < path.len) {
        const value = cp(path, i);
        const end = next(path, i);
        if (value == quote or value == '\\') {
            try output.append(a, '\\');
            try output.append(a, @intCast(value));
        } else if (value == 9) {
            try output.appendSlice(a, "\\t");
        } else if (value == 10) {
            try output.appendSlice(a, "\\n");
        } else if (value == 13) {
            try output.appendSlice(a, "\\r");
        } else if (unicode.properties(value) & 8 != 0) {
            try output.appendSlice(a, path[i..end]);
        } else if (value <= 0xff) {
            try output.appendSlice(a, try std.fmt.allocPrint(a, "\\x{x:0>2}", .{value}));
        } else if (value <= 0xffff) {
            try output.appendSlice(a, try std.fmt.allocPrint(a, "\\u{x:0>4}", .{value}));
        } else try output.appendSlice(a, try std.fmt.allocPrint(a, "\\U{x:0>8}", .{value}));
        i = end;
    }
    try output.append(a, quote);
    return output.items;
}
fn readFailure(init: std.process.Init, path: []const u8, failure: anyerror) !u8 {
    var number: u8 = 5;
    var message: []const u8 = "Input/output error";
    if (failure == error.FileNotFound) {
        number = 2;
        message = "No such file or directory";
    }
    if (failure == error.AccessDenied) {
        number = 13;
        message = "Permission denied";
    }
    if (failure == error.IsDir) {
        number = 21;
        message = "Is a directory";
    }
    if (failure == error.NotDir) {
        number = 20;
        message = "Not a directory";
    }
    if (failure == error.SymLinkLoop) {
        number = @intFromEnum(std.c.E.LOOP);
        message = "Too many levels of symbolic links";
    }
    if (failure == error.NameTooLong) {
        number = @intFromEnum(std.c.E.NAMETOOLONG);
        message = "File name too long";
    }
    try std.Io.File.stderr().writeStreamingAll(init.io, try std.fmt.allocPrint(init.arena.allocator(), "cannot read {s}: [Errno {d}] {s}: {s}\n", .{ path, number, message, try pathRepr(init.arena.allocator(), path) }));
    return 2;
}
fn invalidUtf8(init: std.process.Init, path: []const u8, text: []const u8) !u8 {
    var i: usize = 0;
    while (i < text.len) {
        const width = sequenceWidth(text[i]);
        if (width == 0) break;
        if (i + width > text.len) break;
        _ = std.unicode.utf8Decode(text[i .. i + width]) catch break;
        i += width;
    }
    var end = i + 1;
    var reason: []const u8 = "invalid start byte";
    const width = sequenceWidth(text[i]);
    if (width > 1) {
        reason = "invalid continuation byte";
        var j = i + 1;
        while (j < text.len and j < i + width and text[j] & 0xc0 == 0x80) {
            if (j == i + 1 and ((text[i] == 0xe0 and text[j] < 0xa0) or (text[i] == 0xed and text[j] >= 0xa0) or (text[i] == 0xf0 and text[j] < 0x90) or (text[i] == 0xf4 and text[j] >= 0x90))) break;
            j += 1;
        }
        if (j == text.len and j < i + width) {
            reason = "unexpected end of data";
            end = j;
        } else if (j < i + width) end = j;
    }
    var details = try std.fmt.allocPrint(init.arena.allocator(), "byte 0x{x:0>2} in position {d}", .{ text[i], i });
    if (end > i + 1) details = try std.fmt.allocPrint(init.arena.allocator(), "bytes in position {d}-{d}", .{ i, end - 1 });
    try std.Io.File.stderr().writeStreamingAll(init.io, try std.fmt.allocPrint(init.arena.allocator(), "cannot read {s}: 'utf-8' codec can't decode {s}: {s}\n", .{ path, details, reason }));
    return 2;
}
fn negativeNumber(raw: []const u8) bool {
    // Python argparse's regex $ also anchors before exactly one final LF.
    var argument = raw;
    if (std.mem.endsWith(u8, argument, "\n")) argument = argument[0 .. argument.len - 1];
    if (!starts(argument, "-") or argument.len < 2) return false;
    var i: usize = 1;
    while (i < argument.len and decimal(argument, i)) i = next(argument, i);
    if (i == argument.len) return true;
    if (argument[i] != '.') return false;
    i += 1;
    const first = i;
    while (i < argument.len and decimal(argument, i)) i = next(argument, i);
    return i > first and i == argument.len;
}
// The pinned parser queues help actions while walking recognized short-option
// clusters. Equals/prefix continuations refuse before a queued help can run;
// an unknown suffix instead leaves help queued, so help still exits normally.
fn shortHelpError(argument: []const u8) ?[]const u8 {
    var tail_text = argument[2..];
    while (true) {
        if (tail_text.len > 0 and tail_text[0] == '=') return tail_text[1..];
        if (tail_text.len > 0 and tail_text[0] == '-') return tail_text;
        if (tail_text.len == 0 or tail_text[0] != 'h') return null;
        tail_text = tail_text[1..];
    }
}
fn recognizedLong(argument: []const u8) bool {
    if (!starts(argument, "--")) return false;
    var end = argument.len;
    if (std.mem.indexOfScalar(u8, argument, '=')) |at| end = at;
    return end > 2 and (starts("--help", argument[0..end]) or starts("--changelog", argument[0..end]));
}
fn optionLike(argument: []const u8) bool {
    if (!starts(argument, "-") or argument.len == 1) return false;
    if (starts(argument, "-h") or recognizedLong(argument)) return true;
    if (negativeNumber(argument) or std.mem.indexOfScalar(u8, argument, ' ') != null) return false;
    return true;
}
fn commandRequest(init: std.process.Init, request: Request) !u8 {
    const a = init.arena.allocator();
    if (!validPath(request.repository_root) or !std.fs.path.isAbsolute(request.repository_root) or request.argv.len > 4096) return error.InvalidRequest;
    const root = try std.Io.Dir.cwd().realPathFileAlloc(init.io, request.repository_root, a);
    const root_stat = try std.Io.Dir.cwd().statFile(init.io, root, .{});
    if (!eq(root, request.repository_root) or root_stat.kind != .directory) return error.AmbiguousRepositoryRoot;
    for (request.argv) |argument| {
        if (argument.len > 8192 or std.mem.indexOfScalar(u8, argument, 0) != null or !std.unicode.utf8ValidateSlice(argument)) return error.InvalidRequest;
    }
    // argparse classifies every argument before consuming actions. Its only
    // ambiguous prefix here is -- followed by =; a bare -- ends that pre-scan.
    for (request.argv) |argument| {
        if (eq(argument, "--")) break;
        if (starts(argument, "--=")) return argError(init, try std.fmt.allocPrint(a, "ambiguous option: {s} could match --help, --changelog", .{argument}));
    }
    var selected: []const u8 = "docs/changelog/CHANGELOG.md";
    var unknown: std.ArrayList([]const u8) = .empty;
    var i: usize = 0;
    var ended = false;
    while (i < request.argv.len) {
        const argument = request.argv[i];
        i += 1;
        if (!ended and eq(argument, "--")) {
            ended = true;
            try unknown.append(a, argument);
            continue;
        }
        if (!ended and starts(argument, "-h")) {
            if (shortHelpError(argument)) |explicit| return argError(init, try std.fmt.allocPrint(a, "argument -h/--help: ignored explicit argument {s}", .{try pathRepr(a, explicit)}));
            try emit(init, try helpText(a, try formatterWidth(init)));
            return 0;
        }
        var option = argument;
        var value: ?[]const u8 = null;
        if (!ended and starts(argument, "--")) {
            if (std.mem.indexOfScalar(u8, argument, '=')) |at| {
                option = argument[0..at];
                value = argument[at + 1 ..];
            }
        }
        if (!ended and starts(option, "--") and option.len > 2 and starts("--help", option)) {
            if (value != null) return argError(init, try std.fmt.allocPrint(a, "argument -h/--help: ignored explicit argument {s}", .{try pathRepr(a, value.?)}));
            try emit(init, try helpText(a, try formatterWidth(init)));
            return 0;
        }
        if (!ended and starts(option, "--") and option.len > 2 and starts("--changelog", option)) {
            if (value) |supplied| {
                selected = supplied;
            } else {
                if (i == request.argv.len or optionLike(request.argv[i])) return argError(init, "argument --changelog: expected one argument");
                selected = request.argv[i];
                i += 1;
            }
        } else try unknown.append(a, argument);
    }
    if (unknown.items.len > 0) return argError(init, try std.fmt.allocPrint(a, "unrecognized arguments: {s}", .{try std.mem.join(a, " ", unknown.items)}));
    var path = selected;
    if (!std.fs.path.isAbsolute(selected)) path = try std.mem.concat(a, u8, &.{ root, "/", selected });
    path = try normalizePath(a, path);
    const text = std.Io.Dir.cwd().readFileAlloc(init.io, path, a, .unlimited) catch |failure| return readFailure(init, path, failure);
    if (!std.unicode.utf8ValidateSlice(text)) return invalidUtf8(init, path, text);
    const resolved = try std.Io.Dir.cwd().realPathFileAlloc(init.io, path, a);
    var display = path;
    if (eq(root, "/")) {
        display = resolved[1..];
    } else if (starts(resolved, root) and resolved.len > root.len and resolved[root.len] == '/') display = resolved[root.len + 1 ..];
    const found = try check(a, text, display);
    if (found == null) {
        try emit(init, "no [Unreleased] section found; nothing to check\n");
        return 0;
    }
    var errors: usize = 0;
    for (found.?) |f| {
        var prefix: []const u8 = "";
        if (eq(f.severity, "warning")) {
            prefix = "warning: ";
        } else errors += 1;
        try emit(init, try std.fmt.allocPrint(a, "{s}{s}:{d}: [{s}] {s} — {s}\n", .{ prefix, f.path, f.line, f.rule, f.where, f.fix }));
    }
    try emit(init, try std.fmt.allocPrint(a, "{d} error(s), {d} warning(s)\n", .{ errors, found.?.len - errors }));
    if (errors > 0) return 1;
    return 0;
}
fn readRequest(init: std.process.Init, request_path: []const u8) !u8 {
    const a = init.arena.allocator();
    const raw = try std.Io.Dir.cwd().readFileAlloc(init.io, request_path, a, .limited(1024 * 1024));
    const parsed = try std.json.parseFromSlice(Request, a, raw, .{ .duplicate_field_behavior = .@"error" });
    return commandRequest(init, parsed.value);
}
pub fn command(init: std.process.Init, request_path: []const u8) !u8 {
    return readRequest(init, request_path) catch |failure| {
        try std.Io.File.stderr().writeStreamingAll(init.io, try std.fmt.allocPrint(init.arena.allocator(), "changelog-style request refused: {s}\n", .{@errorName(failure)}));
        return 2;
    };
}
