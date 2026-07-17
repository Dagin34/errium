from collections.abc import Mapping, Sequence
from typing import Any


class ValidationNormalizer:
    def __init__(self, custom_mappings: dict[str, str] | None = None) -> None:
        """Initialize the normalizer with default/custom mappings."""
        # Default maps for validation error types and message strings
        self.mappings = {
            "missing": "{field_name} is required.",
            "value_error.email": "Invalid email format.",
            "value is not a valid email": "Invalid email format.",
            "none is not an allowed value": "Value cannot be empty.",
            "field required": "{field_name} is required.",
        }
        if custom_mappings:
            self.mappings.update(custom_mappings)

    def normalize(self, errors: Sequence[Mapping[str, Any]]) -> dict[str, str]:
        """Normalize a list of validation errors into a flat field-to-message dict.

        Args:
            errors: A sequence of validation error mappings.

        Returns:
            A flat dictionary mapping field paths to formatted messages.
        """
        normalized: dict[str, str] = {}

        for error in errors:
            loc = error.get("loc", [])
            # Convert loc elements to string
            clean_loc = [str(x) for x in loc]

            # Omit FastAPI input location types from the field path
            if clean_loc and clean_loc[0] in (
                "body",
                "query",
                "header",
                "path",
                "formData",
            ):
                clean_loc = clean_loc[1:]

            # The final output key representing the field path
            field_key = ".".join(clean_loc) if clean_loc else "field"

            # Derive a user-friendly field name for message formatting
            raw_field_name = clean_loc[-1] if clean_loc else "field"
            # Format (e.g., 'user_id' -> 'User id')
            field_name = str(raw_field_name).replace("_", " ").capitalize()

            err_type = error.get("type", "")
            err_msg = error.get("msg", "")

            # Look up a template from mapping using type first, then msg
            mapped_template = (
                self.mappings.get(err_type)
                or self.mappings.get(err_msg.lower())
                or self.mappings.get(err_msg)
            )

            # Resilient substring matching fallback
            if not mapped_template:
                for key, val in self.mappings.items():
                    if key in err_msg.lower() or (err_type and key in err_type):
                        mapped_template = val
                        break

            # Fallback to the original message if still not found
            if not mapped_template:
                mapped_template = err_msg

            # Format template with field name if placeholder is present
            if "{field_name}" in str(mapped_template):
                message = mapped_template.format(field_name=field_name)
            else:
                message = str(mapped_template)

            # Clean and standard punctuation: ensure ends with period, capitalized start
            if message:
                if not message.endswith("."):
                    message += "."
                message = message[0].upper() + message[1:]

            normalized[field_key] = message

        return normalized
