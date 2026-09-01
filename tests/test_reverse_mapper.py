from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mapping_reverse.engine import run_reverse_mapping  # noqa: E402
from mapping_reverse.model import ReverseStatus  # noqa: E402
from mapping_reverse.output import write_reverse_output  # noqa: E402


def write_arxml(root: Path, relative: str, body: str, prefix: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    namespace = "urn:test:autosar"
    if prefix:
        body = body.replace("<", f"<{prefix}:").replace(f"<{prefix}:/", f"</{prefix}:")
        text = f'<{prefix}:AUTOSAR xmlns:{prefix}="{namespace}">{body}</{prefix}:AUTOSAR>'
    else:
        text = f'<AUTOSAR xmlns="{namespace}">{body}</AUTOSAR>'
    path.write_text(text, encoding="utf-8")
    return path


def package(elements: str) -> str:
    return f"<AR-PACKAGES><AR-PACKAGE><SHORT-NAME>P</SHORT-NAME><ELEMENTS>{elements}</ELEMENTS></AR-PACKAGE></AR-PACKAGES>"


def service(name: str = "ServiceA", extra: str = "") -> str:
    return package(f"<SERVICE-INTERFACE><SHORT-NAME>{name}</SHORT-NAME><MAJOR-VERSION>1</MAJOR-VERSION>{extra}</SERVICE-INTERFACE>")


def test_renamed_and_moved_arxml_files_preserve_projection(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    write_arxml(first, "a.arxml", service())
    write_arxml(second, "wrapper/deep/renamed.arxml", service())
    left = run_reverse_mapping(first)
    right = run_reverse_mapping(second)
    assert [(row.arxml_tag, row.short_name, row.status) for row in left] == [(row.arxml_tag, row.short_name, row.status) for row in right]


def test_namespace_prefix_does_not_change_projection(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    write_arxml(first, "a.arxml", service())
    write_arxml(second, "a.arxml", service(), "ar")
    assert [(row.arxml_tag, row.short_name) for row in run_reverse_mapping(first)] == [
        (row.arxml_tag, row.short_name) for row in run_reverse_mapping(second)
    ]


def test_added_and_removed_element_changes_rows(tmp_path):
    path = write_arxml(tmp_path, "a.arxml", service())
    before = run_reverse_mapping(tmp_path)
    path.write_text(
        path.read_text().replace("</ELEMENTS>", "<MACHINE-DESIGN><SHORT-NAME>E</SHORT-NAME></MACHINE-DESIGN></ELEMENTS>"), encoding="utf-8"
    )
    after = run_reverse_mapping(tmp_path)
    assert len(after) == len(before) + 1
    path.write_text(path.read_text().replace("<MACHINE-DESIGN><SHORT-NAME>E</SHORT-NAME></MACHINE-DESIGN>", ""), encoding="utf-8")
    assert len(run_reverse_mapping(tmp_path)) == len(before)


def test_renamed_semantic_element_changes_recovered_name(tmp_path):
    path = write_arxml(tmp_path, "a.arxml", service("Alpha"))
    assert next(row for row in run_reverse_mapping(tmp_path) if row.arxml_tag == "SERVICE-INTERFACE").short_name == "Alpha"
    path.write_text(path.read_text().replace("Alpha", "Beta"), encoding="utf-8")
    assert next(row for row in run_reverse_mapping(tmp_path) if row.arxml_tag == "SERVICE-INTERFACE").short_name == "Beta"


def test_connector_preserves_multiple_credible_concepts(tmp_path):
    write_arxml(tmp_path, "a.arxml", package("<ETHERNET-COMMUNICATION-CONNECTOR><SHORT-NAME>C</SHORT-NAME></ETHERNET-COMMUNICATION-CONNECTOR>"))
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "C")
    assert row.status == ReverseStatus.AMBIGUOUS
    assert set(row.ambiguity) == {"ethernet_interface", "topology_connection"}


def test_missing_reference_is_explicit(tmp_path):
    body = package(
        '<ARGUMENTS><ARGUMENT-DATA-PROTOTYPE><SHORT-NAME>x</SHORT-NAME><TYPE-TREF DEST="APPLICATION-ARRAY-DATA-TYPE">/Types/Missing</TYPE-TREF></ARGUMENT-DATA-PROTOTYPE></ARGUMENTS>'  # noqa: E501
    )
    write_arxml(tmp_path, "a.arxml", body)
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "x")
    assert row.status == ReverseStatus.PARTIAL
    assert row.references[0].state == "missing"


def test_missing_datatype_definition_is_not_fabricated(tmp_path):
    body = package(
        '<ARGUMENTS><ARGUMENT-DATA-PROTOTYPE><SHORT-NAME>x</SHORT-NAME><TYPE-TREF DEST="APPLICATION-PRIMITIVE-DATA-TYPE">/Types/Absent</TYPE-TREF></ARGUMENT-DATA-PROTOTYPE></ARGUMENTS>'  # noqa: E501
    )
    write_arxml(tmp_path, "a.arxml", body)
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "x")
    assert row.references[0].targets == ()


def test_duplicate_reference_targets_remain_ambiguous(tmp_path):
    body = (
        "<AR-PACKAGES>"
        "<AR-PACKAGE><SHORT-NAME>A</SHORT-NAME><ELEMENTS><APPLICATION-PRIMITIVE-DATA-TYPE><SHORT-NAME>T</SHORT-NAME></APPLICATION-PRIMITIVE-DATA-TYPE></ELEMENTS></AR-PACKAGE>"  # noqa: E501
        '<AR-PACKAGE><SHORT-NAME>B</SHORT-NAME><ELEMENTS><APPLICATION-PRIMITIVE-DATA-TYPE><SHORT-NAME>T</SHORT-NAME></APPLICATION-PRIMITIVE-DATA-TYPE><ARGUMENTS><ARGUMENT-DATA-PROTOTYPE><SHORT-NAME>x</SHORT-NAME><TYPE-TREF DEST="APPLICATION-PRIMITIVE-DATA-TYPE">/T</TYPE-TREF></ARGUMENT-DATA-PROTOTYPE></ARGUMENTS></ELEMENTS></AR-PACKAGE>'  # noqa: E501
        "</AR-PACKAGES>"
    )
    write_arxml(tmp_path, "a.arxml", body)
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "x")
    assert row.references[0].state == "ambiguous"
    assert row.status == ReverseStatus.PARTIAL


def test_nested_datatype_reference_is_traversed(tmp_path):
    body = package(
        '<APPLICATION-RECORD-DATA-TYPE><SHORT-NAME>Record</SHORT-NAME><TYPE-TREF DEST="APPLICATION-PRIMITIVE-DATA-TYPE">/P/Scalar</TYPE-TREF></APPLICATION-RECORD-DATA-TYPE><APPLICATION-PRIMITIVE-DATA-TYPE><SHORT-NAME>Scalar</SHORT-NAME></APPLICATION-PRIMITIVE-DATA-TYPE>'  # noqa: E501
    )
    write_arxml(tmp_path, "a.arxml", body)
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "Record")
    tree = row.projections[0].recoverable_properties["datatype_tree"]
    assert any(value == "struct" for _, key, value in tree if key == "kind")
    assert row.references[0].state == "resolved"


def test_someip_event_projection(tmp_path):
    write_arxml(
        tmp_path,
        "a.arxml",
        service(extra="<EVENTS><VARIABLE-DATA-PROTOTYPE><SHORT-NAME>E</SHORT-NAME><EVENT-ID>7</EVENT-ID></VARIABLE-DATA-PROTOTYPE></EVENTS>"),
    )
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "E")
    assert row.projections[0].concept == "someip_event"


def test_someip_method_projection(tmp_path):
    write_arxml(
        tmp_path,
        "a.arxml",
        service(extra="<METHODS><CLIENT-SERVER-OPERATION><SHORT-NAME>M</SHORT-NAME><METHOD-ID>8</METHOD-ID></CLIENT-SERVER-OPERATION></METHODS>"),
    )
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "M")
    assert row.status == ReverseStatus.PROJECTED


def test_someip_field_reports_missing_accessor_identifier(tmp_path):
    write_arxml(tmp_path, "a.arxml", service(extra="<FIELDS><FIELD><SHORT-NAME>F</SHORT-NAME><HAS-GETTER>true</HAS-GETTER></FIELD></FIELDS>"))
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "F")
    assert "getter_id" in row.projections[0].missing_properties


def test_ecu_controller_hierarchy_is_recovered(tmp_path):
    body = package(
        "<MACHINE-DESIGN><SHORT-NAME>E</SHORT-NAME><COMMUNICATION-CONTROLLERS><ETHERNET-COMMUNICATION-CONTROLLER><SHORT-NAME>C</SHORT-NAME></ETHERNET-COMMUNICATION-CONTROLLER></COMMUNICATION-CONTROLLERS></MACHINE-DESIGN>"  # noqa: E501
    )
    write_arxml(tmp_path, "a.arxml", body)
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "C")
    assert row.projections[0].recoverable_properties["immediate_owner"] == "E"


def test_unsupported_named_autosar_structure_is_reported(tmp_path):
    write_arxml(tmp_path, "a.arxml", package("<UNSUPPORTED-ELEMENT><SHORT-NAME>X</SHORT-NAME></UNSUPPORTED-ELEMENT>"))
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "X")
    assert row.status == ReverseStatus.UNSUPPORTED


def test_service_missing_flync_service_id_is_partial(tmp_path):
    write_arxml(tmp_path, "a.arxml", service())
    row = next(row for row in run_reverse_mapping(tmp_path) if row.arxml_tag == "SERVICE-INTERFACE")
    assert row.status == ReverseStatus.PARTIAL
    assert "service_id" in row.projections[0].missing_properties


def test_json_output_is_byte_deterministic(tmp_path):
    arxml = tmp_path / "arxml"
    write_arxml(arxml, "a.arxml", service())
    rows = run_reverse_mapping(arxml)
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    write_reverse_output(rows, first)
    write_reverse_output(rows, second)
    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text())["direction"] == "arxml-to-flync-concepts"


def test_csv_output_is_deterministic_and_logically_equivalent(tmp_path):
    arxml = tmp_path / "arxml"
    write_arxml(arxml, "a.arxml", service())
    rows = run_reverse_mapping(arxml)
    first, second = tmp_path / "a.csv", tmp_path / "b.csv"
    write_reverse_output(rows, first)
    write_reverse_output(rows, second)
    assert first.read_bytes() == second.read_bytes()
    assert len(list(csv.DictReader(first.open(encoding="utf-8")))) == len(rows)


def test_concept_filter_returns_only_requested_group(tmp_path):
    write_arxml(
        tmp_path, "a.arxml", service(extra="<METHODS><CLIENT-SERVER-OPERATION><SHORT-NAME>M</SHORT-NAME></CLIENT-SERVER-OPERATION></METHODS>")
    )
    rows = run_reverse_mapping(tmp_path, concept="someip")
    assert rows and all(projection.group == "someip" for row in rows for projection in row.projections)


def test_domain_filter_excludes_adaptive_from_classic(tmp_path):
    write_arxml(tmp_path, "a.arxml", service())
    assert run_reverse_mapping(tmp_path, domain="classic") == ()


def test_can_frame_properties_are_recovered(tmp_path):
    body = package("<CAN-FRAME><SHORT-NAME>F</SHORT-NAME><IDENTIFIER>17</IDENTIFIER><FRAME-LENGTH>8</FRAME-LENGTH></CAN-FRAME>")
    write_arxml(tmp_path, "a.arxml", body)
    row = next(row for row in run_reverse_mapping(tmp_path) if row.short_name == "F")
    assert row.status == ReverseStatus.PROJECTED
    assert row.projections[0].recoverable_properties["can_id"] == "17"


def test_arxml_file_addition_is_discovered_recursively(tmp_path):
    write_arxml(tmp_path, "one/a.arxml", service("A"))
    before = run_reverse_mapping(tmp_path)
    write_arxml(tmp_path, "two/deep/b.arxml", service("B"))
    after = run_reverse_mapping(tmp_path)
    assert len(after) > len(before)


def test_actual_task3_arxml_is_processed_without_fixture_assumptions():
    root = Path(__file__).resolve().parents[1]
    rows = run_reverse_mapping(root / "Adaptive")
    assert rows
    assert any(row.arxml_tag == "MACHINE-DESIGN" for row in rows)
    assert any(row.arxml_tag == "SERVICE-INTERFACE" for row in rows)
