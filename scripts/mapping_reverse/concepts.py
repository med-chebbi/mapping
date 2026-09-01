"""Data-driven registry of repository-supported FLYNC concepts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptSpec:
    name: str
    group: str
    domain: str
    arxml_tags: tuple[str, ...]
    properties: tuple[tuple[str, tuple[str, ...]], ...] = ()
    required: tuple[str, ...] = ("name",)
    normally_unrecoverable: tuple[str, ...] = ()
    transformations: tuple[str, ...] = ()
    ancestor_tags: tuple[str, ...] = ()


CONCEPTS = (
    ConceptSpec("ecu", "ecu", "adaptive", ("MACHINE-DESIGN", "MACHINE", "ECU-INSTANCE"), normally_unrecoverable=("author", "compatible_version")),
    ConceptSpec(
        "controller",
        "controller",
        "shared",
        ("CAN-COMMUNICATION-CONTROLLER", "ETHERNET-COMMUNICATION-CONTROLLER"),
        normally_unrecoverable=("author", "compatible_version", "target_system"),
    ),
    ConceptSpec("can_bus", "can", "classic", ("CAN-CLUSTER",), (("baud_rate", ("BAUDRATE", "BAUD-RATE")),), ("name", "baud_rate")),
    ConceptSpec("can_interface", "can", "classic", ("CAN-COMMUNICATION-CONNECTOR",)),
    ConceptSpec(
        "can_frame",
        "can",
        "classic",
        ("CAN-FRAME", "CAN-FRAME-TRIGGERING"),
        (("can_id", ("IDENTIFIER",)), ("length", ("FRAME-LENGTH",))),
        ("name", "can_id", "length"),
    ),
    ConceptSpec("pdu", "can", "shared", ("I-SIGNAL-I-PDU", "N-PDU"), (("length", ("LENGTH",)),), ("name", "length")),
    ConceptSpec("multiplexed_pdu", "can", "shared", ("MULTIPLEXED-I-PDU",), (("length", ("LENGTH",)),), ("name", "length")),
    ConceptSpec("container_pdu", "can", "adaptive", ("CONTAINER-I-PDU",), (("length", ("LENGTH",)),), ("name", "length")),
    ConceptSpec("signal", "can", "classic", ("I-SIGNAL", "SYSTEM-SIGNAL"), (("bit_length", ("LENGTH",)),), ("name", "bit_length")),
    ConceptSpec("signal_group", "can", "classic", ("I-SIGNAL-GROUP", "SYSTEM-SIGNAL-GROUP")),
    ConceptSpec("ethernet_interface", "ethernet", "adaptive", ("ETHERNET-COMMUNICATION-CONNECTOR", "ETHERNET-PHYSICAL-CHANNEL")),
    ConceptSpec("vlan", "ethernet", "adaptive", ("VLAN",), (("vlan_id", ("VLAN-IDENTIFIER",)),), ("name", "vlan_id")),
    ConceptSpec(
        "network_endpoint",
        "ethernet",
        "adaptive",
        ("NETWORK-ENDPOINT",),
        (("ipv4_address", ("IPV-4-ADDRESS",)), ("ipv6_address", ("IPV-6-ADDRESS",))),
        ("name",),
    ),
    ConceptSpec(
        "socket",
        "ethernet",
        "adaptive",
        ("SOCKET-ADDRESS",),
        (("port", ("PORT-NUMBER",)), ("protocol", ("PROTOCOL",))),
        ("name", "port", "protocol"),
    ),
    ConceptSpec(
        "someip_service",
        "someip",
        "adaptive",
        ("SERVICE-INTERFACE",),
        (("service_id", ("SERVICE-IDENTIFIER",)), ("major_version", ("MAJOR-VERSION",)), ("minor_version", ("MINOR-VERSION",))),
        ("name", "service_id"),
    ),
    ConceptSpec(
        "someip_event",
        "someip",
        "adaptive",
        ("EVENT", "VARIABLE-DATA-PROTOTYPE"),
        (("event_id", ("EVENT-IDENTIFIER", "EVENT-ID")),),
        ("name", "event_id"),
        ancestor_tags=("EVENTS",),
    ),
    ConceptSpec(
        "someip_method",
        "someip",
        "adaptive",
        ("CLIENT-SERVER-OPERATION",),
        (("method_id", ("METHOD-IDENTIFIER", "METHOD-ID")),),
        ("name", "method_id"),
        ancestor_tags=("METHODS",),
    ),
    ConceptSpec(
        "someip_field",
        "someip",
        "adaptive",
        ("FIELD",),
        (
            ("getter_id", ("GETTER-IDENTIFIER",)),
            ("setter_id", ("SETTER-IDENTIFIER",)),
            ("notifier_id", ("NOTIFIER-IDENTIFIER",)),
            ("has_getter", ("HAS-GETTER",)),
            ("has_setter", ("HAS-SETTER",)),
            ("has_notifier", ("HAS-NOTIFIER",)),
        ),
        ("name",),
        ancestor_tags=("FIELDS",),
    ),
    ConceptSpec(
        "eventgroup",
        "someip",
        "adaptive",
        ("EVENT-GROUP", "EVENT-HANDLER"),
        (("eventgroup_id", ("EVENT-GROUP-IDENTIFIER",)),),
        ("name", "eventgroup_id"),
    ),
    ConceptSpec(
        "provider",
        "someip",
        "adaptive",
        ("PROVIDED-SERVICE-INSTANCE",),
        (("instance_id", ("INSTANCE-IDENTIFIER", "INSTANCE-ID")),),
        ("name", "instance_id"),
    ),
    ConceptSpec(
        "consumer",
        "someip",
        "adaptive",
        ("CONSUMED-SERVICE-INSTANCE", "REQUIRED-SERVICE-INSTANCE"),
        (("instance_id", ("INSTANCE-IDENTIFIER", "INSTANCE-ID")),),
        ("name", "instance_id"),
    ),
    ConceptSpec(
        "datatype",
        "datatype",
        "shared",
        (
            "APPLICATION-PRIMITIVE-DATA-TYPE",
            "APPLICATION-RECORD-DATA-TYPE",
            "APPLICATION-ARRAY-DATA-TYPE",
            "IMPLEMENTATION-DATA-TYPE",
            "TYPEDEF",
            "UNION-DATA-TYPE",
            "STRING-DATA-TYPE",
        ),
    ),
    ConceptSpec(
        "datatype_parameter",
        "datatype",
        "adaptive",
        ("ARGUMENT-DATA-PROTOTYPE",),
        (("direction", ("DIRECTION",)),),
        ("name", "datatype_reference"),
        ancestor_tags=("ARGUMENTS",),
    ),
    ConceptSpec(
        "topology_connection",
        "topology",
        "shared",
        ("CONNECTION", "ETHERNET-COMMUNICATION-CONNECTOR"),
        normally_unrecoverable=("source_topology_type",),
    ),
)


BY_TAG = {tag: tuple(spec for spec in CONCEPTS if tag in spec.arxml_tags) for tag in sorted({tag for spec in CONCEPTS for tag in spec.arxml_tags})}
