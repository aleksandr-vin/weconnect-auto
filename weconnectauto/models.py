from typing import Annotated

from pydantic import BaseModel, AwareDatetime, PastDate, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _Config(BaseModel):
    pass


class _CamelConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)


class User(_Config):
    sub: str
    name: str
    given_name: str
    family_name: str
    email: str
    email_verified: bool
    updated_at: AwareDatetime
    picture: str


class Vehicle(_CamelConfig):
    vin: str
    commission_id: str | None
    mod_backend: str


class Relation(_CamelConfig):
    vehicle_nickname: str | None
    relation_id: str
    role_reseted: bool
    date_of_first_use: str | None
    license_plate: str | None
    preferred_contact: str | None
    dealer_id: str | None
    dealer_brand_code: str | None
    dealer_info_changed_timestamp: AwareDatetime | None
    allocated_dealer_country: str | None
    carnet_allocation_timestamp: AwareDatetime
    carnet_allocation_type: str
    carnet_indicator: bool
    brand_code: str | None
    purchase_dealer: str | None
    primary_car: bool
    role: str
    role_last_modified: AwareDatetime
    enrollment_status: str
    enrollment_status_last_modified: AwareDatetime
    known_to_vehicle: bool
    role_status: str
    tags: list[str]
    vehicle: Vehicle


class Relations(_CamelConfig):
    user: dict
    relations: list[Relation]
    is_complete_response: bool
    no_information_from: list


class VehicleData(_CamelConfig):
    vin: str
    model_name: str
    exterior_color: str


class VehicleDetails(_CamelConfig):
    class Specification(_CamelConfig):
        code_text: str
        origin: str

    model_name: str
    engine: str
    specifications: list[Specification]
    model_year: str
    exterior_color_text: str
    importer_id: str | None


class Packages(_CamelConfig):
    class Download(_CamelConfig):
        translation_key: str
        link: str
        size_GB: Annotated[float, Field(..., alias="sizeGB")]
        updated_at: PastDate
        provider: str
        is_map_complete: bool
        is_size_sensitive: bool

    manuals: dict[str, str]
    downloads: list[Download]
    MIB: Annotated[str, Field(..., alias="MIB")]


class UserCaps(_CamelConfig):
    class Data(_CamelConfig):
        id: str
        status: list[int]
        expiration_date: AwareDatetime | None = None
        user_disabling_allowed: bool

    data: list[Data]


class WarningLights(_CamelConfig):
    class Data(_CamelConfig):
        class WL(_CamelConfig):
            text: str
            category: str
            priority: str
            icon: str
            icon_name: str
            message_id: str
            customer_relevance: str
            icon_color: str

        car_captured_timestamp: AwareDatetime
        mileage_km: int
        warning_lights: list[WL]

    data: Data


class LastTripdata(_CamelConfig):
    class Data(_CamelConfig):
        id: str
        trip_end_timestamp: AwareDatetime
        trip_type: str
        vehicle_type: str
        mileage_km: Annotated[float | None, Field(..., alias="mileage_km")]
        mileage_mi: Annotated[float | None, Field(..., alias="mileage_mi")]
        start_mileage_km: Annotated[float | None, Field(..., alias="startMileage_km")]
        start_mileage_mi: Annotated[float | None, Field(..., alias="startMileage_mi")]
        overall_mileage_km: Annotated[
            float | None, Field(..., alias="overallMileage_km")
        ]
        overall_mileage_mi: Annotated[
            float | None, Field(..., alias="overallMileage_mi")
        ]
        travel_time: float | None
        average_fuel_consumption: float | None
        average_fuel_consumption_unit: str
        average_electric_consumption: float | None
        average_electric_consumption_unit: str
        average_gas_consumption: float | None
        average_aux_consumption: float | None
        average_recuperation: float | None
        average_speed_kmph: Annotated[
            float | None, Field(..., alias="averageSpeed_kmph")
        ]
        average_speed_mph: Annotated[float | None, Field(..., alias="averageSpeed_mph")]

    data: Data
