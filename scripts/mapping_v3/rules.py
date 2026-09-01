"""Reusable semantic mapping rules over normalized FLYNC and ARXML models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .arxml import ArxmlIndex
from .datatypes import compare_datatypes, normalize_arxml_datatype
from .model import ArxmlElement, Evidence, FlyncElement, MatchResult


@dataclass(frozen=True)
class RuleSpec:
    category: str
    tags: tuple[str, ...]
    property_map: tuple[tuple[str, tuple[str, ...], bool], ...] = ()


@dataclass(frozen=True)
class CandidateAssessment:
    candidate: ArxmlElement
    anchors: tuple[str, ...]
    supporting: tuple[str, ...]


RULES = {
    rule.category: rule
    for rule in (
        RuleSpec("system", ("SYSTEM", "SYSTEM-MAPPING", "MACHINE-DESIGN")),
        RuleSpec("ecu", ("ECU-INSTANCE", "MACHINE-DESIGN", "MACHINE")),
        RuleSpec("controller", ("CAN-COMMUNICATION-CONTROLLER", "ETHERNET-COMMUNICATION-CONTROLLER")),
        RuleSpec("ecu_port", ("ETHERNET-PHYSICAL-PORT", "PHYSICAL-PORT")),
        RuleSpec("can_bus", ("CAN-CLUSTER",), (("baud_rate", ("BAUDRATE", "BAUD-RATE"), False),)),
        RuleSpec("can_interface", ("CAN-COMMUNICATION-CONNECTOR", "CAN-COMMUNICATION-CONTROLLER")),
        RuleSpec("can_frame", ("CAN-FRAME-TRIGGERING", "CAN-FRAME"), (("can_id", ("IDENTIFIER",), True), ("length", ("FRAME-LENGTH",), True))),
        RuleSpec(
            "pdu",
            ("I-SIGNAL-I-PDU", "MULTIPLEXED-I-PDU", "CONTAINER-I-PDU", "N-PDU"),
            (("length", ("LENGTH",), True), ("pdu_id", ("HEADER-ID-LONG-HEADER", "HEADER-ID"), False)),
        ),
        RuleSpec("signal", ("I-SIGNAL", "SYSTEM-SIGNAL"), (("bit_length", ("LENGTH",), True), ("bit_position", ("START-POSITION",), True))),
        RuleSpec("signal_group", ("I-SIGNAL-GROUP", "SYSTEM-SIGNAL-GROUP"), (("bit_position", ("START-POSITION",), True),)),
        RuleSpec(
            "pdu_containment",
            ("CONTAINED-I-PDU-PROPS", "CONTAINER-I-PDU"),
            (("pdu_id", ("HEADER-ID-LONG-HEADER", "HEADER-ID"), True), ("offset", ("OFFSET",), False)),
        ),
        RuleSpec("ethernet_interface", ("ETHERNET-COMMUNICATION-CONTROLLER", "ETHERNET-COMMUNICATION-CONNECTOR")),
        RuleSpec(
            "vlan_interface", ("VLAN", "ETHERNET-PHYSICAL-CHANNEL", "ETHERNET-COMMUNICATION-CONNECTOR"), (("vlan_id", ("VLAN-IDENTIFIER",), True),)
        ),
        RuleSpec("vlan", ("VLAN", "ETHERNET-PHYSICAL-CHANNEL"), (("id", ("VLAN-IDENTIFIER",), True),)),
        RuleSpec(
            "network_endpoint",
            ("NETWORK-ENDPOINT",),
            (("address", ("IPV-4-ADDRESS", "IPV-6-ADDRESS"), True), ("ipv4netmask", ("NETWORK-MASK",), False)),
        ),
        RuleSpec("multicast", ("NETWORK-ENDPOINT",), (("address", ("IPV-4-ADDRESS", "IPV-6-ADDRESS"), True),)),
        RuleSpec("switch", ("ETHERNET-SWITCH", "SWITCH")),
        RuleSpec("switch_port", ("ETHERNET-SWITCH-PORT", "SWITCH-PORT"), (("silicon_port_no", ("PORT-NUMBER",), False),)),
        RuleSpec(
            "socket",
            ("SOCKET-ADDRESS",),
            (("port_no", ("PORT-NUMBER",), True), ("protocol", ("PROTOCOL",), True), ("endpoint_address", ("IPV-4-ADDRESS",), True)),
        ),
        RuleSpec(
            "service_deployment",
            ("PROVIDED-SERVICE-INSTANCE", "CONSUMED-SERVICE-INSTANCE", "REQUIRED-SERVICE-INSTANCE", "SERVICE-INSTANCE"),
            (
                ("service", ("SERVICE-IDENTIFIER",), True),
                ("instance_id", ("INSTANCE-IDENTIFIER", "INSTANCE-ID"), True),
                ("major_version", ("MAJOR-VERSION",), False),
            ),
        ),
        RuleSpec("tcp_profile", ("TCP-TP", "TCP-TP-CONFIG"), (("tcp_profile_id", ("TCP-PROFILE-ID",), True),)),
        RuleSpec(
            "someip_service",
            ("SERVICE-INTERFACE", "PROVIDED-SERVICE-INSTANCE", "CONSUMED-SERVICE-INSTANCE"),
            (("id", ("SERVICE-IDENTIFIER",), True), ("major_version", ("MAJOR-VERSION",), True), ("minor_version", ("MINOR-VERSION",), True)),
        ),
        RuleSpec("someip_event", ("VARIABLE-DATA-PROTOTYPE", "EVENT"), (("id", ("EVENT-IDENTIFIER", "EVENT-ID"), True),)),
        RuleSpec("someip_method", ("CLIENT-SERVER-OPERATION",), (("id", ("METHOD-IDENTIFIER", "METHOD-ID"), True),)),
        RuleSpec(
            "someip_field",
            ("FIELD",),
            (
                ("getter_id", ("GETTER-IDENTIFIER",), True),
                ("setter_id", ("SETTER-IDENTIFIER",), True),
                ("notifier_id", ("NOTIFIER-IDENTIFIER",), True),
            ),
        ),
        RuleSpec("eventgroup", ("EVENT-HANDLER", "EVENT-GROUP"), (("id", ("EVENT-GROUP-IDENTIFIER",), True),)),
        RuleSpec(
            "service_discovery",
            ("SOMEIP-SD-CONFIG", "SOCKET-ADDRESS", "NETWORK-ENDPOINT"),
            (("ip_address", ("IPV-4-ADDRESS",), True), ("port", ("PORT-NUMBER",), True)),
        ),
        RuleSpec("sd_timing", ("SOMEIP-SD-TIMING-CONFIG", "SD-TIMING-CONFIG")),
        RuleSpec("someip_timing", ("SOMEIP-TIMING-CONFIG",)),
        RuleSpec("topology", ("CONNECTION", "ETHERNET-COMMUNICATION-CONNECTOR", "CAN-COMMUNICATION-CONNECTOR", "PHYSICAL-CHANNEL")),
    )
}


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if value is None:
        return None
    text = str(value).strip()
    try:
        return int(text, 0)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text.lower() if text.lower() in {"true", "false"} else text


def _values(candidate: ArxmlElement, leaves: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value for leaf in leaves for value in candidate.properties.get(leaf, ()))


def _context_evidence(element: FlyncElement, candidate: ArxmlElement) -> tuple[tuple[str, ...], tuple[str, ...]]:
    anchors: list[str] = []
    supporting: list[str] = []
    if element.name == candidate.short_name:
        supporting.append("exact-name")
        anchors.append("compatible-concept-type")
    elif candidate.short_name and element.name in candidate.short_name:
        supporting.append("similar-name")
    for key, value in element.context.items():
        if value is not None and str(value) in candidate.hierarchy:
            anchors.append(f"context:{key}")
    return tuple(anchors), tuple(supporting)


def _property_evidence(
    element: FlyncElement, candidate: ArxmlElement, available: tuple[ArxmlElement, ...], spec: RuleSpec, index: ArxmlIndex
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    anchors: list[str] = []
    supporting: list[str] = []
    for key, leaves, _ in spec.property_map:
        expected = element.properties.get(key)
        actual = _values(candidate, leaves)
        if expected is not None and any(normalize_scalar(expected) == normalize_scalar(value) for value in actual):
            matching = tuple(
                item for item in available if any(normalize_scalar(expected) == normalize_scalar(value) for value in _values(item, leaves))
            )
            if key in {"port", "port_no"} or (isinstance(normalize_scalar(expected), int) and len(matching) > 1):
                supporting.append(f"property:{key}")
            else:
                anchors.append(f"property:{key}")
    if element.category == "socket":
        expected_ip = element.properties.get("endpoint_address")
        if expected_ip is not None:
            for reference in candidate.references:
                resolution = index.resolve(reference.value, candidate, reference.dest)
                for key in resolution.candidates:
                    target = index.by_key[key]
                    if any(normalize_scalar(expected_ip) == normalize_scalar(value) for value in target.properties.get("IPV-4-ADDRESS", ())):
                        anchors.append("resolved-endpoint-ip")
    return tuple(sorted(set(anchors))), tuple(sorted(set(supporting)))


def select_candidates(element: FlyncElement, index: ArxmlIndex, spec: RuleSpec) -> tuple[ArxmlElement, ...]:
    available = tuple(candidate for tag in spec.tags for candidate in index.by_tag.get(tag, ()))
    if not available:
        return ()
    assessments = []
    for candidate in available:
        context_anchors, context_support = _context_evidence(element, candidate)
        property_anchors, property_support = _property_evidence(element, candidate, available, spec, index)
        assessments.append(CandidateAssessment(candidate, context_anchors + property_anchors, context_support + property_support))
    credible = tuple(item for item in assessments if item.anchors)
    if not credible:
        return ()
    strongest = max((len(item.anchors), len(item.supporting)) for item in credible)
    return tuple(sorted((item.candidate for item in credible if (len(item.anchors), len(item.supporting)) == strongest), key=lambda item: item.key))


def resolve_element(element: FlyncElement, index: ArxmlIndex) -> tuple[tuple[ArxmlElement, ...], tuple[Evidence, ...]]:
    if element.category == "datatype":
        return _resolve_datatype(element, index)
    spec = RULES.get(element.category)
    if spec is None:
        return (), (Evidence("supported-category", MatchResult.MISSING, True, element.category, None, (), "no V3 semantic rule is registered"),)
    candidates = select_candidates(element, index, spec)
    evidence: list[Evidence] = []
    if not candidates:
        name_hints = tuple(
            sorted(
                (candidate for tag in spec.tags for candidate in index.by_tag.get(tag, ()) if candidate.short_name == element.name),
                key=lambda item: item.key,
            )
        )
        weak = (
            (
                Evidence(
                    "short-name",
                    MatchResult.SUPPORTING,
                    False,
                    element.name,
                    tuple(item.short_name for item in name_hints),
                    tuple(item.key for item in name_hints),
                    "name match is a diagnostic hint and cannot establish a candidate",
                ),
            )
            if name_hints
            else ()
        )
        return (), weak + (Evidence("candidate", MatchResult.MISSING, True, element.name, None, (), "no independent semantic anchor"),)
    keys = tuple(candidate.key for candidate in candidates)
    names = tuple(candidate.short_name for candidate in candidates)
    exact_name = any(element.name == name for name in names)
    evidence.append(
        Evidence(
            "short-name",
            MatchResult.SUPPORTING if exact_name else MatchResult.TRANSFORMED,
            False,
            element.name,
            names,
            keys,
            "name is supporting evidence only",
        )
    )
    evidence.append(
        Evidence(
            "element-type",
            MatchResult.SUPPORTING,
            False,
            element.category,
            tuple(candidate.tag for candidate in candidates),
            keys,
            "candidate AUTOSAR concept type",
        )
    )
    if len(candidates) > 1:
        evidence.append(
            Evidence(
                "candidate-context",
                MatchResult.AMBIGUOUS,
                True,
                element.context,
                names,
                keys,
                "multiple equally ranked context-compatible candidates",
            )
        )
    for key, leaves, required in spec.property_map:
        expected = element.properties.get(key)
        if expected is None:
            continue
        actual = tuple(value for candidate in candidates for value in _values(candidate, leaves))
        if not actual:
            result = MatchResult.MISSING
            actual_value: Any = None
        elif any(normalize_scalar(expected) == normalize_scalar(value) for value in actual):
            result = MatchResult.MATCH
            actual_value = actual[0] if len(actual) == 1 else actual
        else:
            result = MatchResult.MISMATCH
            actual_value = actual[0] if len(actual) == 1 else actual
        evidence.append(Evidence(key, result, required, expected, actual_value, keys, f"compared against {', '.join(leaves)}"))
    evidence.extend(_special_evidence(element, candidates, index))
    return candidates, tuple(evidence)


def _special_evidence(element: FlyncElement, candidates: tuple[ArxmlElement, ...], index: ArxmlIndex) -> list[Evidence]:
    evidence: list[Evidence] = []
    keys = tuple(candidate.key for candidate in candidates)
    if element.category == "socket":
        property_map = {
            "port": ("PORT-NUMBER",),
            "protocol": ("PROTOCOL", "TCP-UDP-CONFIG"),
            "ip": ("IPV-4-ADDRESS",),
            "vlan": ("VLAN-IDENTIFIER",),
        }
        for key, leaves in property_map.items():
            expected = element.context.get(key)
            if expected is None:
                continue
            actual = tuple(value for candidate in candidates for value in _values(candidate, leaves))
            result = (
                MatchResult.MATCH
                if any(normalize_scalar(expected) == normalize_scalar(value) for value in actual)
                else MatchResult.MISSING if not actual else MatchResult.MISMATCH
            )
            evidence.append(
                Evidence(f"socket-{key}", result, key in {"port", "protocol", "ip"}, expected, actual or None, keys, "composite socket context")
            )
    for candidate in candidates:
        for reference in candidate.references:
            resolution = index.resolve(reference.value, candidate, reference.dest)
            result = {"resolved": MatchResult.MATCH, "ambiguous": MatchResult.AMBIGUOUS, "missing": MatchResult.UNRESOLVED}[resolution.state]
            evidence.append(
                Evidence(
                    f"reference:{reference.kind}", result, False, reference.value, resolution.state, resolution.candidates, resolution.rationale
                )
            )
    return evidence


def _resolve_datatype(element: FlyncElement, index: ArxmlIndex) -> tuple[tuple[ArxmlElement, ...], tuple[Evidence, ...]]:
    parameter_candidates = [candidate for candidate in index.by_tag.get("ARGUMENT-DATA-PROTOTYPE", ()) if candidate.short_name == element.name]
    if not parameter_candidates:
        parameter_candidates = [candidate for candidate in index.by_tag.get("VARIABLE-DATA-PROTOTYPE", ()) if candidate.short_name == element.name]
    if not parameter_candidates:
        return (), (Evidence("datatype-parameter", MatchResult.MISSING, True, element.name, None, (), "no ARXML parameter prototype"),)
    candidates = tuple(sorted(parameter_candidates, key=lambda item: item.key))
    evidence: list[Evidence] = []
    if len(candidates) > 1:
        evidence.append(
            Evidence(
                "datatype-parameter",
                MatchResult.AMBIGUOUS,
                True,
                element.name,
                tuple(item.short_name for item in candidates),
                tuple(item.key for item in candidates),
                "parameter name is not unique across context",
            )
        )
    for candidate in candidates:
        type_refs = [reference for reference in candidate.references if "TYPE" in reference.kind]
        if not type_refs:
            evidence.append(
                Evidence(
                    "datatype-reference",
                    MatchResult.MISSING,
                    True,
                    element.datatype.kind if element.datatype else None,
                    None,
                    (candidate.key,),
                    "parameter has no datatype reference",
                )
            )
            continue
        for reference in type_refs:
            resolution = index.resolve(reference.value, candidate, reference.dest)
            if resolution.state != "resolved":
                result = MatchResult.AMBIGUOUS if resolution.state == "ambiguous" else MatchResult.UNRESOLVED
                evidence.append(
                    Evidence("datatype-reference", result, True, reference.value, resolution.state, resolution.candidates, resolution.rationale)
                )
                continue
            target = index.by_key[resolution.candidates[0]]
            if element.datatype:
                evidence.extend(compare_datatypes(element.datatype, normalize_arxml_datatype(target, index), target.key))
    return candidates, tuple(evidence)
