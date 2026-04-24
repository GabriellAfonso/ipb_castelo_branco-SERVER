import pytest
from pydantic import ValidationError

from core.application.dtos.strict_base import StrictBaseModel


class SampleDTO(StrictBaseModel):
    name: str
    age: int


class TestStrictBaseModel:
    def test_valid_data_accepted(self) -> None:
        dto = SampleDTO(name="Alice", age=30)
        assert dto.name == "Alice"
        assert dto.age == 30

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            SampleDTO(name="Alice", age=30, email="a@b.com")  # type: ignore[call-arg]

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            SampleDTO(name="Alice")  # type: ignore[call-arg]

    def test_wrong_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            SampleDTO(name="Alice", age="not_a_number")  # type: ignore[arg-type]
