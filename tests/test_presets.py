from milpcrypt.presets import (
    PRESETS,
    get_preset,
    list_presets,
    resolve_sbox,
)


def test_preset_list():
    keys = [preset.key for preset in list_presets()]
    assert keys == ["present", "prince", "prince-inverse", "klein"]
    assert set(PRESETS) == set(keys)


def test_preset_aliases():
    assert get_preset("PRESENT").to_hex == get_preset("present").to_hex
    assert (
        get_preset("prince_inv").to_hex
        == get_preset("prince-inverse").to_hex
    )
    assert get_preset("princeinverse").to_hex == get_preset(
        "prince-inverse"
    ).to_hex


def test_resolve_inline_hex():
    sbox = resolve_sbox("c56b90ad3ef84712")
    assert sbox.name == "custom"
    assert sbox.to_hex == "C56B90AD3EF84712"


def test_resolve_file(tmp_path):
    path = tmp_path / "my_sbox.txt"
    path.write_text("c56b90ad3ef84712\n", encoding="utf-8")
    sbox = resolve_sbox(str(path))
    assert sbox.name == "my_sbox"
    assert sbox.to_hex == "C56B90AD3EF84712"


def test_unknown_preset_message():
    try:
        get_preset("not-a-cipher")
    except ValueError as exc:
        assert "available" in str(exc)
    else:
        raise AssertionError("expected ValueError")
