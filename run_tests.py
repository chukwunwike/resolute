#!/usr/bin/env python3
"""
Standalone test runner for resolute — no pytest required.
"""
import sys
import traceback
import warnings
import asyncio

sys.path.insert(0, "/home/claude/resolute")

from resolute import (
    Ok, Err, Result, Some, Nothing, Option,
    UnwrapError, SafeDecoratorError,
    safe, safe_async,
    collect, collect_all, partition, flatten_result,
    sequence, transpose, transpose_result,
)

passed = 0
failed = 0
_errors = []

def assert_(condition, msg="assertion failed"):
    if not condition:
        raise AssertionError(msg)

def get_original(fn):
    try:
        fn()
    except UnwrapError as e:
        return e.original
    return None

def raises(exc_type, fn):
    try:
        fn()
        return False
    except exc_type:
        return True
    except Exception:
        return False

def run(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS  {name}")
    except Exception as e:
        failed += 1
        _errors.append((name, traceback.format_exc()))
        print(f"  FAIL  {name}  ->  {e}")

# ============================================================
# Result — state inspection
# ============================================================
print("\n--- Result: state inspection ---")
run("ok_is_ok",              lambda: assert_(Ok(1).is_ok() is True))
run("ok_is_not_err",         lambda: assert_(Ok(1).is_err() is False))
run("err_is_err",            lambda: assert_(Err("x").is_err() is True))
run("err_is_not_ok",         lambda: assert_(Err("x").is_ok() is False))
run("ok_and_pred_true",      lambda: assert_(Ok(5).is_ok_and(lambda x: x > 3)))
run("ok_and_pred_false",     lambda: assert_(not Ok(2).is_ok_and(lambda x: x > 3)))
run("err_ok_and_false",      lambda: assert_(not Err("x").is_ok_and(lambda x: True)))
run("err_and_pred_true",     lambda: assert_(Err("bad").is_err_and(lambda e: "bad" in e)))
run("ok_err_and_false",      lambda: assert_(not Ok(1).is_err_and(lambda e: True)))

# ============================================================
# Result — unwrap variants
# ============================================================
print("\n--- Result: unwrap ---")
run("ok_unwrap",             lambda: assert_(Ok(42).unwrap() == 42))
run("err_unwrap_raises",     lambda: assert_(raises(UnwrapError, lambda: Err("x").unwrap())))
run("unwrap_err_original",   lambda: assert_(get_original(lambda: Err("hello").unwrap()) == "hello"))
run("ok_unwrap_or",          lambda: assert_(Ok(1).unwrap_or(99) == 1))
run("err_unwrap_or",         lambda: assert_(Err("x").unwrap_or(99) == 99))
run("ok_unwrap_or_else",     lambda: assert_(Ok(5).unwrap_or_else(lambda e: 0) == 5))
run("err_unwrap_or_else",    lambda: assert_(Err("bad").unwrap_or_else(lambda e: len(e)) == 3))
run("ok_unwrap_or_raise",    lambda: assert_(Ok(7).unwrap_or_raise(ValueError()) == 7))
run("err_unwrap_or_raise",   lambda: assert_(raises(ValueError, lambda: Err("x").unwrap_or_raise(ValueError("no")))))
run("err_unwrap_err",        lambda: assert_(Err("e").unwrap_err() == "e"))
run("ok_unwrap_err_raises",  lambda: assert_(raises(UnwrapError, lambda: Ok(1).unwrap_err())))
run("ok_expect",             lambda: assert_(Ok(3).expect("msg") == 3))
run("err_expect_raises",     lambda: assert_(raises(UnwrapError, lambda: Err("x").expect("msg"))))
run("err_expect_err",        lambda: assert_(Err("bad").expect_err("msg") == "bad"))
run("ok_expect_err_raises",  lambda: assert_(raises(UnwrapError, lambda: Ok(1).expect_err("msg"))))

# ============================================================
# Result — map
# ============================================================
print("\n--- Result: map ---")
run("map_ok",                lambda: assert_(Ok(2).map(lambda x: x * 3) == Ok(6)))
run("map_err_passthrough",   lambda: assert_(Err("bad").map(lambda x: x * 3) == Err("bad")))
run("map_err_transforms",    lambda: assert_(Err("bad").map_err(str.upper) == Err("BAD")))
run("map_err_ok_passes",     lambda: assert_(Ok(1).map_err(str.upper) == Ok(1)))
run("map_or_ok",             lambda: assert_(Ok(2).map_or(0, lambda x: x * 3) == 6))
run("map_or_err",            lambda: assert_(Err("bad").map_or(0, lambda x: x * 3) == 0))
run("map_or_else_ok",        lambda: assert_(Ok(2).map_or_else(lambda e: 0, lambda x: x * 3) == 6))
run("map_or_else_err",       lambda: assert_(Err("bad").map_or_else(lambda e: len(e), lambda x: 0) == 3))

# ============================================================
# Result — chaining
# ============================================================
print("\n--- Result: chaining ---")
safe_div = lambda x: Ok(10 / x) if x != 0 else Err("div0")
run("and_then_ok",           lambda: assert_(Ok(2).and_then(safe_div) == Ok(5.0)))
run("and_then_ok_to_err",    lambda: assert_(Ok(0).and_then(safe_div) == Err("div0")))
run("and_then_short_circuit",lambda: assert_(Err("p").and_then(safe_div) == Err("p")))
run("or_else_ok_passes",     lambda: assert_(Ok(1).or_else(lambda e: Ok(0)) == Ok(1)))
run("or_else_recovers",      lambda: assert_(Err("bad").or_else(lambda e: Ok(99)) == Ok(99)))
run("or_else_remaps",        lambda: assert_(Err("bad").or_else(lambda e: Err(e.upper())) == Err("BAD")))
run("and_ok",                lambda: assert_(Ok(1).and_(Ok(2)) == Ok(2)))
run("and_err",               lambda: assert_(Err("x").and_(Ok(2)) == Err("x")))
run("or_ok",                 lambda: assert_(Ok(1).or_(Ok(99)) == Ok(1)))
run("or_err",                lambda: assert_(Err("x").or_(Ok(99)) == Ok(99)))

# ============================================================
# Result — ok/err conversion to Option
# ============================================================
print("\n--- Result: Option conversion ---")
run("ok_to_some",            lambda: assert_(Ok(1).ok() == Some(1)))
run("err_ok_to_nothing",     lambda: assert_(Err("x").ok() is Nothing))
run("err_err_to_some",       lambda: assert_(Err("x").err() == Some("x")))
run("ok_err_to_nothing",     lambda: assert_(Ok(1).err() is Nothing))

# ============================================================
# Result — dunder / data model
# ============================================================
print("\n--- Result: dunder ---")
run("ok_repr",               lambda: assert_(repr(Ok(42)) == "Ok(42)"))
run("err_repr",              lambda: assert_(repr(Err("x")) == "Err('x')"))
run("ok_eq",                 lambda: assert_(Ok(1) == Ok(1)))
run("ok_neq",                lambda: assert_(Ok(1) != Ok(2)))
run("ok_err_neq",            lambda: assert_(Ok(1) != Err(1)))
run("err_eq",                lambda: assert_(Err("x") == Err("x")))
run("ok_hashable",           lambda: assert_(len({Ok(1), Ok(1), Ok(2)}) == 2))
run("err_hashable",          lambda: assert_(len({Err("a"), Err("a"), Err("b")}) == 2))
run("ok_truthy",             lambda: assert_(bool(Ok(0)) is True))
run("err_falsy",             lambda: assert_(bool(Err("x")) is False))
run("ok_iter",               lambda: assert_(list(Ok(5)) == [5]))
run("err_iter_empty",        lambda: assert_(list(Err("x")) == []))
run("comprehension_flatten", lambda: assert_(
    [x for r in [Ok(1), Err("skip"), Ok(3)] for x in r] == [1, 3]
))

# ============================================================
# Option — state inspection
# ============================================================
print("\n--- Option: state inspection ---")
run("some_is_some",          lambda: assert_(Some(1).is_some()))
run("some_not_nothing",      lambda: assert_(not Some(1).is_nothing()))
run("nothing_is_nothing",    lambda: assert_(Nothing.is_nothing()))
run("nothing_not_some",      lambda: assert_(not Nothing.is_some()))
run("some_and_pred_true",    lambda: assert_(Some(4).is_some_and(lambda x: x > 3)))
run("some_and_pred_false",   lambda: assert_(not Some(2).is_some_and(lambda x: x > 3)))
run("nothing_some_and",      lambda: assert_(not Nothing.is_some_and(lambda x: True)))

# ============================================================
# Option — unwrap
# ============================================================
print("\n--- Option: unwrap ---")
run("some_unwrap",           lambda: assert_(Some(42).unwrap() == 42))
run("nothing_unwrap_raises", lambda: assert_(raises(UnwrapError, lambda: Nothing.unwrap())))
run("some_unwrap_or",        lambda: assert_(Some(1).unwrap_or(99) == 1))
run("nothing_unwrap_or",     lambda: assert_(Nothing.unwrap_or(99) == 99))
run("some_unwrap_or_else",   lambda: assert_(Some(1).unwrap_or_else(lambda: 99) == 1))
run("nothing_unwrap_or_else",lambda: assert_(Nothing.unwrap_or_else(lambda: 99) == 99))
run("some_unwrap_or_raise",  lambda: assert_(Some(1).unwrap_or_raise(ValueError()) == 1))
run("nothing_unwrap_or_raise",lambda: assert_(raises(TypeError, lambda: Nothing.unwrap_or_raise(TypeError()))))
run("some_expect",           lambda: assert_(Some(1).expect("msg") == 1))
run("nothing_expect_raises", lambda: assert_(raises(UnwrapError, lambda: Nothing.expect("msg"))))

# ============================================================
# Option — transform
# ============================================================
print("\n--- Option: transform ---")
run("some_map",              lambda: assert_(Some(2).map(lambda x: x * 3) == Some(6)))
run("nothing_map",           lambda: assert_(Nothing.map(lambda x: x * 3) is Nothing))
run("some_map_or",           lambda: assert_(Some(2).map_or(0, lambda x: x * 3) == 6))
run("nothing_map_or",        lambda: assert_(Nothing.map_or(0, lambda x: x * 3) == 0))
run("some_filter_pass",      lambda: assert_(Some(4).filter(lambda x: x > 3) == Some(4)))
run("some_filter_fail",      lambda: assert_(Some(2).filter(lambda x: x > 3) is Nothing))
run("nothing_filter",        lambda: assert_(Nothing.filter(lambda x: True) is Nothing))

# ============================================================
# Option — chaining
# ============================================================
print("\n--- Option: chaining ---")
dbl = lambda x: Some(x * 2) if x > 0 else Nothing
run("some_and_then",         lambda: assert_(Some(3).and_then(dbl) == Some(6)))
run("some_and_then_nothing", lambda: assert_(Some(-1).and_then(dbl) is Nothing))
run("nothing_and_then",      lambda: assert_(Nothing.and_then(dbl) is Nothing))
run("some_or_else_passes",   lambda: assert_(Some(1).or_else(lambda: Some(99)) == Some(1)))
run("nothing_or_else",       lambda: assert_(Nothing.or_else(lambda: Some(99)) == Some(99)))
run("some_and_some",         lambda: assert_(Some(1).and_(Some(2)) == Some(2)))
run("nothing_and",           lambda: assert_(Nothing.and_(Some(2)) is Nothing))
run("some_or",               lambda: assert_(Some(1).or_(Some(99)) == Some(1)))
run("nothing_or",            lambda: assert_(Nothing.or_(Some(99)) == Some(99)))
run("zip_some_some",         lambda: assert_(Some(1).zip(Some("a")) == Some((1, "a"))))
run("zip_some_nothing",      lambda: assert_(Some(1).zip(Nothing) is Nothing))
run("zip_nothing_some",      lambda: assert_(Nothing.zip(Some("a")) is Nothing))
run("flatten_some_some",     lambda: assert_(Some(Some(1)).flatten() == Some(1)))
run("flatten_some_nothing",  lambda: assert_(Some(Nothing).flatten() is Nothing))
run("flatten_nothing",       lambda: assert_(Nothing.flatten() is Nothing))

# ============================================================
# Option — Result conversion
# ============================================================
print("\n--- Option: Result conversion ---")
run("some_ok_or",            lambda: assert_(Some(1).ok_or("miss") == Ok(1)))
run("nothing_ok_or",         lambda: assert_(Nothing.ok_or("miss") == Err("miss")))
run("some_ok_or_else",       lambda: assert_(Some(1).ok_or_else(lambda: "miss") == Ok(1)))
run("nothing_ok_or_else",    lambda: assert_(Nothing.ok_or_else(lambda: "miss") == Err("miss")))

# ============================================================
# Option — dunder
# ============================================================
print("\n--- Option: dunder ---")
run("some_repr",             lambda: assert_(repr(Some(42)) == "Some(42)"))
run("nothing_repr",          lambda: assert_(repr(Nothing) == "Nothing"))
run("some_eq",               lambda: assert_(Some(1) == Some(1)))
run("some_neq",              lambda: assert_(Some(1) != Some(2)))
run("some_neq_nothing",      lambda: assert_(Some(1) != Nothing))
run("nothing_eq",            lambda: assert_(Nothing == Nothing))
run("some_hashable",         lambda: assert_(len({Some(1), Some(1), Some(2)}) == 2))
run("nothing_singleton",     lambda: assert_(Nothing is Nothing))
run("some_truthy",           lambda: assert_(bool(Some(0)) is True))
run("nothing_falsy",         lambda: assert_(bool(Nothing) is False))
run("some_iter",             lambda: assert_(list(Some(5)) == [5]))
run("nothing_iter_empty",    lambda: assert_(list(Nothing) == []))
run("option_comprehension",  lambda: assert_(
    [x for o in [Some(1), Nothing, Some(3)] for x in o] == [1, 3]
))

# ============================================================
# @safe decorator
# ============================================================
print("\n--- @safe ---")

@safe(catch=ValueError)
def parse(s):
    return int(s)

run("safe_ok",               lambda: assert_(parse("42") == Ok(42)))
run("safe_err",              lambda: assert_(parse("abc").is_err()))
run("safe_err_is_valueerror",lambda: assert_(isinstance(parse("abc").unwrap_err(), ValueError)))
run("safe_reraises_uncaught",lambda: assert_(raises(TypeError, lambda: parse(None))))

@safe(catch=(ValueError, KeyError))
def lookup(d, k):
    return int(d[k])

run("safe_multi_ok",         lambda: assert_(lookup({"a": "5"}, "a") == Ok(5)))
run("safe_multi_keyerr",     lambda: assert_(lookup({}, "a").is_err()))
run("safe_multi_valerr",     lambda: assert_(lookup({"a": "x"}, "a").is_err()))
run("safe_preserves_name",   lambda: assert_(parse.__name__ == "parse"))

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    @safe(catch=Exception)
    def broad_fn():
        return 1
run("safe_broad_warns",      lambda: assert_(any(issubclass(w.category, RuntimeWarning) for w in caught)))

with warnings.catch_warnings(record=True) as caught2:
    warnings.simplefilter("always")
    @safe(catch=Exception, allow_broad=True)
    def broad_fn2():
        return 1
run("safe_allow_broad_no_warn", lambda: assert_(not any(issubclass(w.category, RuntimeWarning) for w in caught2)))

run("safe_forbid_keyboard_interrupt",
    lambda: assert_(raises(SafeDecoratorError, lambda: safe(catch=KeyboardInterrupt)(lambda: None))))
run("safe_forbid_system_exit",
    lambda: assert_(raises(SafeDecoratorError, lambda: safe(catch=SystemExit)(lambda: None))))
run("safe_forbid_generator_exit",
    lambda: assert_(raises(SafeDecoratorError, lambda: safe(catch=GeneratorExit)(lambda: None))))

# ============================================================
# @safe_async decorator
# ============================================================
print("\n--- @safe_async ---")

@safe_async(catch=ValueError)
async def async_parse(s):
    return int(s)

def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

run("safe_async_ok",         lambda: assert_(run_async(async_parse("42")) == Ok(42)))
run("safe_async_err",        lambda: assert_(run_async(async_parse("abc")).is_err()))
run("safe_async_reraises",   lambda: assert_(raises(TypeError, lambda: run_async(async_parse(None)))))
run("safe_async_name",       lambda: assert_(async_parse.__name__ == "async_parse"))

# ============================================================
# Combinators
# ============================================================
print("\n--- collect ---")
run("collect_all_ok",        lambda: assert_(collect([Ok(1), Ok(2), Ok(3)]) == Ok([1, 2, 3])))
run("collect_first_err",     lambda: assert_(collect([Ok(1), Err("bad"), Ok(3)]) == Err("bad")))
run("collect_empty",         lambda: assert_(collect([]) == Ok([])))

print("\n--- collect_all ---")
run("collect_all_ok2",       lambda: assert_(collect_all([Ok(1), Ok(2)]) == Ok([1, 2])))
run("collect_all_errs",      lambda: assert_(collect_all([Ok(1), Err("a"), Err("b")]) == Err(["a", "b"])))
run("collect_all_mixed",     lambda: assert_(collect_all([Err("a"), Err("b")]) == Err(["a", "b"])))
run("collect_all_empty",     lambda: assert_(collect_all([]) == Ok([])))

print("\n--- partition ---")
run("partition_mixed",       lambda: assert_(partition([Ok(1), Err("a"), Ok(2)]) == ([1, 2], ["a"])))
run("partition_all_ok",      lambda: assert_(partition([Ok(1), Ok(2)]) == ([1, 2], [])))
run("partition_all_err",     lambda: assert_(partition([Err("x"), Err("y")]) == ([], ["x", "y"])))
run("partition_empty",       lambda: assert_(partition([]) == ([], [])))

print("\n--- flatten_result ---")
run("flatten_ok_ok",         lambda: assert_(flatten_result(Ok(Ok(1))) == Ok(1)))
run("flatten_ok_err",        lambda: assert_(flatten_result(Ok(Err("x"))) == Err("x")))
run("flatten_outer_err",     lambda: assert_(flatten_result(Err("outer")) == Err("outer")))

print("\n--- sequence ---")
run("sequence_all_some",     lambda: assert_(sequence([Some(1), Some(2)]) == Some([1, 2])))
run("sequence_nothing",      lambda: assert_(sequence([Some(1), Nothing]) is Nothing))
run("sequence_empty",        lambda: assert_(sequence([]) == Some([])))

print("\n--- transpose ---")
run("transpose_some_ok",     lambda: assert_(transpose(Some(Ok(1))) == Ok(Some(1))))
run("transpose_some_err",    lambda: assert_(transpose(Some(Err("x"))) == Err("x")))
run("transpose_nothing",     lambda: assert_(transpose(Nothing).unwrap() is Nothing))

print("\n--- transpose_result ---")
run("tr_ok_some",            lambda: assert_(transpose_result(Ok(Some(1))) == Some(Ok(1))))
run("tr_ok_nothing",         lambda: assert_(transpose_result(Ok(Nothing)) is Nothing))
run("tr_err",                lambda: assert_(transpose_result(Err("x")) == Some(Err("x"))))

# ============================================================
# Integration
# ============================================================
print("\n--- Integration ---")

def validate_age(s):
    try:
        age = int(s)
    except ValueError:
        return Err("age must be a number")
    if not (0 < age < 150):
        return Err("age out of range")
    return Ok(age)

def validate_name(s):
    s = s.strip()
    return Ok(s) if s else Err("name required")

run("collect_all_validation", lambda: assert_(
    collect_all([validate_name(""), validate_age("abc")]).unwrap_err() == ["name required", "age must be a number"]
))

run("railway_chain", lambda: assert_(
    Ok("5")
    .and_then(lambda s: Ok(int(s)) if s.isdigit() else Err("not int"))
    .and_then(lambda n: Ok(n * 2) if n > 0 else Err("not positive"))
    == Ok(10)
))

run("result_as_dict_key", lambda: assert_(
    {Ok("k"): "value"}[Ok("k")] == "value"
))

run("option_lookup_chain", lambda: assert_(
    Some({"email_id": 10})
    .and_then(lambda u: Some(u["email_id"]) if "email_id" in u else Nothing)
    .and_then(lambda eid: Some(f"user-{eid}"))
    == Some("user-10")
))

# ============================================================
# Summary
# ============================================================
print(f"\n{'='*50}")
print(f"  {passed} passed   {failed} failed   {passed+failed} total")
print(f"{'='*50}")

if _errors:
    print("\nFailed tests:")
    for name, tb in _errors:
        print(f"\n=== {name} ===")
        print(tb)
    sys.exit(1)
