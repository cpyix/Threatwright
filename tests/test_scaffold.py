from pathlib import Path

import pytest
from typer.testing import CliRunner

from threatwright.branding import PROJECT_FILE
from threatwright.cli import ProductType, app
from threatwright.model.store import Project
from threatwright.scaffold import PRODUCT_LIBRARIES, create_project


def zone_ids(path: Path) -> list[str]:
    return [z.id for z in Project.load(path).models["main"].meta.zones]


def test_create_project_libraries(tmp_path: Path) -> None:
    create_project(tmp_path / "a")
    assert Project.load(tmp_path / "a").config.libraries == ["ot"]
    assert "Z-PLANT" in zone_ids(tmp_path / "a")

    create_project(tmp_path / "b", libraries=["software", "iot", "iot"])
    assert Project.load(tmp_path / "b").config.libraries == ["iot", "software"]
    ids = zone_ids(tmp_path / "b")
    assert "Z-LAN" in ids and "Z-PLANT" not in ids

    for bad in ([], ["foo"]):
        with pytest.raises(ValueError):
            create_project(tmp_path / "c", libraries=bad)
        assert not (tmp_path / "c" / PROJECT_FILE).exists()


def test_init_library_option(tmp_path: Path) -> None:
    r = CliRunner().invoke(app, ["init", str(tmp_path / "p"), "-l", "iot", "--library", "software"])
    assert r.exit_code == 0, r.output
    assert Project.load(tmp_path / "p").config.libraries == ["iot", "software"]
    assert CliRunner().invoke(app, ["init", str(tmp_path / "q"), "--library", "foo"]).exit_code != 0


def test_cli_product_types_match_scaffold() -> None:
    assert [t.value for t in ProductType] == list(PRODUCT_LIBRARIES)


def test_embedded_linux_brings_ot(tmp_path: Path) -> None:
    requested = ["embedded-linux"]
    create_project(tmp_path / "e", libraries=requested)
    assert requested == ["embedded-linux"]  # caller's list untouched
    assert Project.load(tmp_path / "e").config.libraries == ["ot", "embedded-linux"]
    assert "Z-PLANT" in zone_ids(tmp_path / "e")
    r = CliRunner().invoke(app, ["init", str(tmp_path / "f"), "-l", "embedded-linux"])
    assert r.exit_code == 0, r.output
