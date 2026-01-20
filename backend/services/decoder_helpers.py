"""
Decoder Type Detection and Validation

Centralized decoder type detection and CV write validation logic.

Decoder Types:
- esu_mfx: ESU LokSound/LokPilot decoders using mfx speed table style
  - CV67 (step 1) = FIXED at 1 (not editable)
  - CV94 (step 28) = FIXED at 255 (not editable)
  - CV68-93 (step 2-27) = SCALED between CV2 (Vstart) and CV5 (Vhigh)

- nmra_standard: NMRA standard decoders (Hornby TXS, Zimo, etc.)
  - CV67-94 (step 1-28) = All editable (0-255)
"""

from config_loader import load_config


# Decoder type mapping (decoder name substring -> decoder type)
DECODER_TYPE_MAP = {
    "LokSound": "esu_mfx",
    "LokPilot": "esu_mfx",
    "Hornby TXS": "nmra_standard",
    "MX630": "nmra_standard",  # Zimo
}


def get_decoder_type_from_config(loco_address: int) -> str:
    """
    Detect decoder type from config.json locomotive metadata.

    Args:
        loco_address: Locomotive DCC address (1-10239)

    Returns:
        Decoder type string: "esu_mfx" or "nmra_standard"

    Example:
        >>> get_decoder_type_from_config(1)  # Gr.675 017
        'esu_mfx'  # LokSound V4.0

        >>> get_decoder_type_from_config(7)  # E656 239
        'nmra_standard'  # Hornby TXS
    """
    config = load_config()

    # Get locomotive config
    loco_config = config.get("locomotives", {}).get(str(loco_address))
    if not loco_config:
        # Unknown locomotive - safe default
        return "nmra_standard"

    decoder_name = loco_config.get("decoder", "")

    # Match decoder name against known patterns
    for key, value in DECODER_TYPE_MAP.items():
        if key in decoder_name:
            return value

    # Default to NMRA standard if not recognized
    return "nmra_standard"


def validate_cv_write_allowed(loco_address: int, cv_index: int, decoder_type: str):
    """
    Validate if CV write is allowed for this decoder type.

    Raises ValueError if write is blocked (ESU step 1/28).

    Args:
        loco_address: Locomotive DCC address
        cv_index: CV index to write (67-94)
        decoder_type: Decoder type ("esu_mfx" or "nmra_standard")

    Raises:
        ValueError: If CV write is blocked (ESU CV67 or CV94)

    Example:
        >>> validate_cv_write_allowed(1, 67, "esu_mfx")
        ValueError: CV67 (step 1) is read-only for ESU decoders (fixed at 1). Edit CV2 (Vstart) instead.

        >>> validate_cv_write_allowed(1, 70, "esu_mfx")
        # No exception - CV70 is editable for ESU

        >>> validate_cv_write_allowed(7, 67, "nmra_standard")
        # No exception - All CVs editable for NMRA
    """
    if decoder_type == "esu_mfx":
        if cv_index == 67:
            raise ValueError(
                f"CV67 (step 1) is read-only for ESU decoders (fixed at 1). "
                f"Edit CV2 (Vstart) instead. [Loco {loco_address}]"
            )
        if cv_index == 94:
            raise ValueError(
                f"CV94 (step 28) is read-only for ESU decoders (fixed at 255). "
                f"Edit CV5 (Vhigh) instead. [Loco {loco_address}]"
            )

    # NMRA standard: All CVs editable, no validation needed


def enforce_esu_fixed_values(cv_values: dict, decoder_type: str) -> dict:
    """
    Force CV67=1, CV94=255 for ESU decoders (immutable endpoints).

    Args:
        cv_values: Dict mapping CV index (67-94) to value (0-255)
        decoder_type: Decoder type ("esu_mfx" or "nmra_standard")

    Returns:
        Modified cv_values dict with ESU fixed values enforced

    Example:
        >>> cv_values = {67: 0, 68: 10, ..., 94: 200}
        >>> enforce_esu_fixed_values(cv_values, "esu_mfx")
        {67: 1, 68: 10, ..., 94: 255}  # CV67 forced to 1, CV94 forced to 255

        >>> enforce_esu_fixed_values(cv_values, "nmra_standard")
        {67: 0, 68: 10, ..., 94: 200}  # No changes for NMRA
    """
    if decoder_type == "esu_mfx":
        cv_values[67] = 1
        cv_values[94] = 255

    return cv_values
