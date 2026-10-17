//! Source-bound statement inventory for the qualified local-validation grammar.
//! Every AST node keeps a role; collection alone never accepts coverage. Runtime
//! statements include controlled bodies, switch arms, deferred/catch bodies, and
//! embedded return/break/continue. Unsupported instrumentation semantics refuse.
const std = @import("std");
const Ast = std.zig.Ast;
const Span = struct { start: u32, end: u32 };
const Scope = struct { span: Span, function: bool = false, test_only: bool = false, explicit_comptime: bool = false };
const Unit = struct { node: u32, tag: []const u8, start: u32, end: u32, line: usize, column: usize, origins: u8 };
const Accounting = struct { node: u32, tag: []const u8, start: u32, end: u32, main: u32, role: []const u8, origins: u8 };
const limit = 16 * 1024 * 1024;

fn span(tree: Ast, node: Ast.Node.Index) Span {
    const first = tree.firstToken(node);
    const last = tree.lastToken(node);
    return .{ .start = tree.tokenStart(first), .end = tree.tokenStart(last) + @as(u32, @intCast(tree.tokenSlice(last).len)) };
}

fn structural(tree: Ast, node: Ast.Node.Index) bool {
    var buffer: [2]Ast.Node.Index = undefined;
    return node == .root or tree.blockStatements(&buffer, node) != null;
}

fn add(nodes: *std.AutoHashMap(u32, u8), tree: Ast, node: Ast.Node.Index, origin: u8) !void {
    if (structural(tree, node)) return;
    const entry = try nodes.getOrPut(@intFromEnum(node));
    if (!entry.found_existing) entry.value_ptr.* = 0;
    entry.value_ptr.* |= origin;
}

fn supported(tag: Ast.Node.Tag) bool {
    // This is a transform boundary, not a filter: an unqualified runtime unit
    // fails the whole inventory instead of disappearing from the denominator.
    const tags = [_]Ast.Node.Tag{
        .simple_var_decl,
        .assign,
        .assign_destructure,
        .assign_add,
        .assign_add_sat,
        .assign_add_wrap,
        .assign_bit_and,
        .assign_bit_or,
        .assign_bit_xor,
        .assign_div,
        .assign_mod,
        .assign_mul,
        .assign_mul_sat,
        .assign_mul_wrap,
        .assign_shl,
        .assign_shl_sat,
        .assign_shr,
        .assign_sub,
        .assign_sub_sat,
        .assign_sub_wrap,
        .if_simple,
        .@"if",
        .while_simple,
        .while_cont,
        .@"while",
        .for_simple,
        .@"for",
        .@"switch",
        .switch_comma,
        .@"return",
        .@"defer",
        .@"errdefer",
        .@"try",
        .call,
        .call_one,
        .builtin_call_two,
        .builtin_call_two_comma,
        .builtin_call,
        .builtin_call_comma,
        .@"catch",
        .@"continue",
        .@"break",
    };
    for (tags) |candidate| {
        if (tag == candidate) return true;
    }
    return false;
}

fn less(_: void, left: Unit, right: Unit) bool {
    if (left.start == right.start) return left.node < right.node;
    return left.start < right.start;
}

fn inventory(allocator: std.mem.Allocator, source: [:0]const u8) ![]const u8 {
    var tree = try Ast.parse(allocator, source, .zig);
    defer tree.deinit(allocator);
    if (tree.errors.len != 0) return error.ParseRefused;
    var nodes = std.AutoHashMap(u32, u8).init(allocator);
    defer nodes.deinit();
    var scopes: std.ArrayList(Scope) = .empty;
    defer scopes.deinit(allocator);
    for (0..tree.nodes.len) |number| {
        const node: Ast.Node.Index = @enumFromInt(number);
        const tag = tree.nodeTag(node);
        if (tag == .fn_decl) {
            try scopes.append(allocator, .{ .span = span(tree, tree.nodeData(node).node_and_node[1]), .function = true });
        }
        if (tag == .test_decl) try scopes.append(allocator, .{ .span = span(tree, node), .test_only = true });
        var explicit_comptime = tag == .@"comptime";
        if (tree.fullVarDecl(node)) |decl| explicit_comptime = explicit_comptime or decl.comptime_token != null;
        if (explicit_comptime) try scopes.append(allocator, .{ .span = span(tree, node), .explicit_comptime = true });
        var buffer: [2]Ast.Node.Index = undefined;
        if (tree.blockStatements(&buffer, node)) |statements| {
            for (statements) |statement| try add(&nodes, tree, statement, 1);
        }
        if (tree.fullIf(node)) |info| {
            try add(&nodes, tree, info.ast.then_expr, 2);
            if (info.ast.else_expr.unwrap()) |child| try add(&nodes, tree, child, 2);
        }
        if (tree.fullFor(node)) |info| {
            try add(&nodes, tree, info.ast.then_expr, 4);
            if (info.ast.else_expr.unwrap()) |child| try add(&nodes, tree, child, 4);
        }
        if (tree.fullWhile(node)) |info| {
            try add(&nodes, tree, info.ast.then_expr, 4);
            if (info.ast.cont_expr.unwrap()) |child| try add(&nodes, tree, child, 4);
            if (info.ast.else_expr.unwrap()) |child| try add(&nodes, tree, child, 4);
        }
        if (tree.fullSwitch(node)) |info| {
            for (info.ast.cases) |case_node| {
                const case = tree.fullSwitchCase(case_node) orelse return error.UnsupportedStatement;
                // Inline prongs have compile-time execution rules of their own.
                // Keep them refused until a paired transform proves that seam.
                if (case.inline_token != null) return error.UnsupportedStatement;
                try add(&nodes, tree, case.ast.target_expr, 64);
            }
        }
        // Transfers are expressions too: an orelse/catch initializer can hide
        // one from all direct block/control statement lists.
        if (tag == .@"return" or tag == .@"break" or tag == .@"continue") try add(&nodes, tree, node, 8);
        if (tag == .@"defer") try add(&nodes, tree, tree.nodeData(node).node, 16);
        if (tag == .@"errdefer") try add(&nodes, tree, tree.nodeData(node).opt_token_and_node[1], 16);
        if (tag == .@"catch") try add(&nodes, tree, tree.nodeData(node).node_and_node[1], 32);
    }
    var units: std.ArrayList(Unit) = .empty;
    defer units.deinit(allocator);
    var accounting: std.ArrayList(Accounting) = .empty;
    defer accounting.deinit(allocator);
    for (0..tree.nodes.len) |number| {
        const node: Ast.Node.Index = @enumFromInt(number);
        const location = span(tree, node);
        const tag = tree.nodeTag(node);
        var function = false;
        var test_only = false;
        var explicit_comptime = false;
        for (scopes.items) |scope| {
            if (scope.span.start <= location.start and location.end <= scope.span.end) {
                function = function or scope.function;
                test_only = test_only or scope.test_only;
                explicit_comptime = explicit_comptime or scope.explicit_comptime;
            }
        }
        const origins = nodes.get(@intCast(number)) orelse 0;
        var inline_for = false;
        if (tree.fullFor(node)) |info| inline_for = info.inline_token != null;
        var role: []const u8 = "declaration";
        if (structural(tree, node)) role = "structural";
        if (function and !structural(tree, node)) role = "runtime-expression";
        if (function and origins != 0) role = "runtime-statement";
        if (inline_for) role = "compile-time-control";
        if (explicit_comptime) role = "explicit-comptime";
        if (test_only) role = "test-only";
        if (function and !test_only and !explicit_comptime and !inline_for) {
            if (origins != 0) {
                const direct_statement = origins & (1 | 8) != 0;
                const controlled_body = origins & (2 | 4 | 16 | 32 | 64) != 0;
                if (direct_statement and !supported(tag)) return error.UnsupportedStatement;
                if (!direct_statement and !controlled_body) return error.UnsupportedStatement;
                var line: usize = 1;
                var column: usize = 1;
                for (source[0..location.start]) |byte| {
                    if (byte == '\n') {
                        line += 1;
                        column = 1;
                    } else column += 1;
                }
                try units.append(allocator, .{ .node = @intCast(number), .tag = @tagName(tag), .start = location.start, .end = location.end, .line = line, .column = column, .origins = origins });
            }
        }
        try accounting.append(allocator, .{ .node = @intCast(number), .tag = @tagName(tag), .start = location.start, .end = location.end, .main = tree.tokenStart(tree.nodeMainToken(node)), .role = role, .origins = origins });
    }
    std.mem.sort(Unit, units.items, {}, less);
    var digest: [std.crypto.hash.sha2.Sha256.digest_length]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(source, &digest, .{});
    const hex = std.fmt.bytesToHex(digest, .lower);
    var output: std.Io.Writer.Allocating = .init(allocator);
    defer output.deinit();
    var stringify: std.json.Stringify = .{ .writer = &output.writer };
    try stringify.write(.{ .schema_version = 1, .source_sha256 = hex[0..], .coverage_accepted = false, .units = units.items, .all_ast_node_accounting = accounting.items });
    try output.writer.writeByte('\n');
    return try allocator.dupe(u8, output.written());
}

fn run(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len != 2 and args.len != 4) return error.InvalidArguments;
    if (args.len == 4 and !std.mem.eql(u8, args[2], "--verify")) return error.InvalidArguments;
    const bytes = try std.Io.Dir.cwd().readFileAlloc(init.io, args[1], allocator, .limited(limit));
    const source = try allocator.dupeZ(u8, bytes);
    const rendered = try inventory(allocator, source);
    if (args.len == 4) {
        const supplied = try std.Io.Dir.cwd().readFileAlloc(init.io, args[3], allocator, .limited(limit));
        // Exact canonical comparison binds every role, unit, duplicate and byte
        // offset to the current source, without trusting a supplied denominator.
        if (!std.mem.eql(u8, supplied, rendered)) return error.InventoryMismatch;
        return;
    }
    try std.Io.File.stdout().writeStreamingAll(init.io, rendered);
}

pub fn main(init: std.process.Init) !void {
    run(init) catch |err| std.process.fatal("statement inventory refused: {t}", .{err});
}
