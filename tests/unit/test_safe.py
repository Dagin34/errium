from errium_core.safe import safe_str, truncate


class BadStr(Exception):
    def __str__(self) -> str:
        raise RuntimeError("str is broken")


class BadStrAndRepr(Exception):
    def __str__(self) -> str:
        raise RuntimeError("str is broken")

    def __repr__(self) -> str:
        raise RuntimeError("repr is broken")


class Unprintable:
    def __repr__(self) -> str:
        raise RuntimeError("cannot repr")

    def __str__(self) -> str:
        raise RuntimeError("cannot str")


class NonStringStr(Exception):
    def __str__(self) -> str:
        return 42  # type: ignore[return-value]


def test_safe_str_plain_message():
    assert safe_str(ValueError("boom")) == "boom"


def test_safe_str_falls_back_to_repr():
    assert "BadStr" in safe_str(BadStr())


def test_safe_str_falls_back_to_class_name():
    assert safe_str(BadStrAndRepr()) == "BadStrAndRepr"


def test_safe_str_unprintable_args():
    assert safe_str(ValueError(Unprintable())) == "ValueError"


def test_safe_str_non_string_str_does_not_raise():
    assert isinstance(safe_str(NonStringStr()), str)


def test_safe_str_truncates_to_limit():
    text = safe_str(ValueError("x" * 100_000))
    assert len(text) == 2000
    assert text.endswith("...[truncated]")


def test_safe_str_custom_limit():
    assert len(safe_str(ValueError("y" * 500), limit=100)) == 100


def test_truncate_noop_when_short():
    assert truncate("abc", 10) == "abc"
