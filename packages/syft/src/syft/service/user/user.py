# stdlib
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

# third party
from bcrypt import checkpw
from bcrypt import gensalt
from bcrypt import hashpw
import pydantic
from pydantic.networks import EmailStr

# relative
from ...client.api import APIRegistry
from ...node.credentials import SyftSigningKey
from ...node.credentials import SyftVerifyKey
from ...serde.serializable import serializable
from ...types.syft_object import PartialSyftObject
from ...types.syft_object import SYFT_OBJECT_VERSION_1
from ...types.syft_object import SyftObject
from ...types.transforms import TransformContext
from ...types.transforms import drop
from ...types.transforms import generate_id
from ...types.transforms import keep
from ...types.transforms import make_set_default
from ...types.transforms import transform
from ...types.transforms import validate_email
from ...types.uid import UID
from ..response import SyftError
from ..response import SyftSuccess
from .user_roles import ServiceRole


@serializable()
class User(SyftObject):
    # version
    __canonical_name__ = "User"
    __version__ = SYFT_OBJECT_VERSION_1

    id: Optional[UID]

    @pydantic.validator("email", pre=True, always=True)
    def make_email(cls, v: EmailStr) -> EmailStr:
        return EmailStr(v)

    # fields
    email: Optional[EmailStr]
    name: Optional[str]
    hashed_password: Optional[str]
    salt: Optional[str]
    signing_key: Optional[SyftSigningKey]
    verify_key: Optional[SyftVerifyKey]
    role: Optional[ServiceRole]
    institution: Optional[str]
    website: Optional[str] = None
    created_at: Optional[str] = None

    # serde / storage rules
    __attr_searchable__ = ["name", "email", "verify_key", "role"]
    __attr_unique__ = ["email", "signing_key", "verify_key"]
    __repr_attrs__ = ["name", "email"]


def default_role(role: ServiceRole) -> Callable:
    return make_set_default(key="role", value=role)


def hash_password(context: TransformContext) -> TransformContext:
    if context.output["password"] is not None and (
        (context.output["password_verify"] is None)
        or context.output["password"] == context.output["password_verify"]
    ):
        salt, hashed = salt_and_hash_password(context.output["password"], 12)
        context.output["hashed_password"] = hashed
        context.output["salt"] = salt
    return context


def generate_key(context: TransformContext) -> TransformContext:
    signing_key = SyftSigningKey.generate()
    context.output["signing_key"] = signing_key
    context.output["verify_key"] = signing_key.verify_key
    return context


def salt_and_hash_password(password: str, rounds: int) -> Tuple[str, str]:
    bytes_pass = password.encode("UTF-8")
    salt = gensalt(rounds=rounds)
    hashed = hashpw(bytes_pass, salt)
    hashed_bytes = hashed.decode("UTF-8")
    salt_bytes = salt.decode("UTF-8")
    return salt_bytes, hashed_bytes


def check_pwd(password: str, hashed_password: str) -> bool:
    return checkpw(
        password=password.encode("utf-8"),
        hashed_password=hashed_password.encode("utf-8"),
    )


@serializable()
class UserUpdate(PartialSyftObject):
    __canonical_name__ = "UserUpdate"
    __version__ = SYFT_OBJECT_VERSION_1

    @pydantic.validator("email", pre=True)
    def make_email(cls, v: EmailStr) -> Optional[EmailStr]:
        return EmailStr(v) if isinstance(v, str) else v

    email: EmailStr
    name: str
    role: ServiceRole  # make sure role cant be set without uid
    password: str
    password_verify: str
    verify_key: SyftVerifyKey
    institution: str
    website: str


@serializable()
class UserCreate(UserUpdate):
    __canonical_name__ = "UserCreate"
    __version__ = SYFT_OBJECT_VERSION_1

    email: EmailStr
    name: str
    role: Optional[ServiceRole] = None  # make sure role cant be set without uid
    password: str
    password_verify: Optional[str] = None
    verify_key: Optional[SyftVerifyKey]
    institution: Optional[str]
    website: Optional[str]
    created_by: Optional[SyftSigningKey]

    __repr_attrs__ = ["name", "email"]


@serializable()
class UserSearch(PartialSyftObject):
    __canonical_name__ = "UserSearch"
    __version__ = SYFT_OBJECT_VERSION_1

    id: UID
    email: EmailStr
    verify_key: SyftVerifyKey
    name: str


@serializable()
class UserView(SyftObject):
    __canonical_name__ = "UserView"
    __version__ = SYFT_OBJECT_VERSION_1

    email: EmailStr
    name: str
    role: ServiceRole  # make sure role cant be set without uid
    institution: Optional[str]
    website: Optional[str]

    __repr_attrs__ = ["name", "email", "institution", "website", "role"]

    def _coll_repr_(self) -> Dict[str, Any]:
        return {
            "Name": self.name,
            "Email": self.email,
            "Institute": self.institution,
            "Website": self.website,
            "Role": self.role.name.capitalize(),
        }

    def set_password(self, new_password: str) -> Union[SyftSuccess, SyftError]:
        api = APIRegistry.api_for(
            node_uid=self.syft_node_location,
            user_verify_key=self.syft_client_verify_key,
        )
        if api is None:
            return SyftError(message=f"You must login to {self.node_uid}")
        api.services.user.update(
            uid=self.id, user_update=UserUpdate(password=new_password)
        )

        return SyftSuccess(
            message=f"Successfully setting a new password for "
            f"user '{self.name}' with email '{self.email}'."
        )

    def set_name(self, new_name: str) -> Union[SyftSuccess, SyftError]:
        api = APIRegistry.api_for(
            node_uid=self.syft_node_location,
            user_verify_key=self.syft_client_verify_key,
        )
        if api is None:
            return SyftError(message=f"You must login to {self.node_uid}")
        api.services.user.update(uid=self.id, user_update=UserUpdate(name=new_name))
        self.name = new_name
        return SyftSuccess(
            message=f"Successfully setting a new name for the user "
            f"with email '{self.email}'. New name is '{self.name}'."
        )

    def set_email(self, new_email: EmailStr) -> Union[SyftSuccess, SyftError]:
        api = APIRegistry.api_for(
            node_uid=self.syft_node_location,
            user_verify_key=self.syft_client_verify_key,
        )
        if api is None:
            return SyftError(message=f"You must login to {self.node_uid}")
        api.services.user.update(uid=self.id, user_update=UserUpdate(email=new_email))
        self.email = new_email
        return SyftSuccess(
            message=f"Successfully setting a new email for the user "
            f"'{self.name}'. New email is '{self.email}'."
        )

    def set_institute(self, new_institute: str) -> Union[SyftSuccess, SyftError]:
        api = APIRegistry.api_for(
            node_uid=self.syft_node_location,
            user_verify_key=self.syft_client_verify_key,
        )
        if api is None:
            return SyftError(message=f"You must login to {self.node_uid}")
        api.services.user.update(
            uid=self.id, user_update=UserUpdate(institution=new_institute)
        )
        self.institution = new_institute
        return SyftSuccess(
            message=f"Successfully setting a new institute for the user "
            f"'{self.name}' with email '{self.email}'. "
            f"New institute is '{self.institution}'."
        )

    def set_website(self, new_website: str) -> Union[SyftSuccess, SyftError]:
        api = APIRegistry.api_for(
            node_uid=self.syft_node_location,
            user_verify_key=self.syft_client_verify_key,
        )
        if api is None:
            return SyftError(message=f"You must login to {self.node_uid}")
        api.services.user.update(
            uid=self.id, user_update=UserUpdate(website=new_website)
        )
        self.website = new_website
        return SyftSuccess(
            message=f"Successfully setting a new website for the user "
            f"'{self.name}' with email '{self.email}'. "
            f"New website is '{self.website}'."
        )

    def set_role(self, new_role: str) -> Union[SyftSuccess, SyftError]:
        if new_role == "guest":
            update_role = ServiceRole.GUEST
        elif new_role == "data_scientist":
            update_role = ServiceRole.DATA_SCIENTIST
        elif new_role == "data_owner":
            update_role = ServiceRole.DATA_OWNER
        elif new_role == "admin":
            update_role = ServiceRole.ADMIN
        else:
            return SyftError(
                message=f"Can't set role to {new_role}. Please try "
                f"admin / data_scientist / data_owner / guest."
            )
        api = APIRegistry.api_for(
            node_uid=self.syft_node_location,
            user_verify_key=self.syft_client_verify_key,
        )
        if api is None:
            return SyftError(message=f"You must login to {self.node_uid}")
        api.services.user.update(uid=self.id, user_update=UserUpdate(role=update_role))
        self.role = update_role
        return SyftSuccess(
            message=f"Successfully setting a new role for the user "
            f"'{self.name}' with email '{self.email}'. New role is '{new_role}'."
        )


@serializable()
class UserViewPage(SyftObject):
    __canonical_name__ = "UserViewPage"
    __version__ = SYFT_OBJECT_VERSION_1

    users: List[UserView]
    total: int


@transform(UserUpdate, User)
def user_update_to_user() -> List[Callable]:
    return [
        validate_email,
        hash_password,
        drop(["password", "password_verify"]),
    ]


@transform(UserCreate, User)
def user_create_to_user() -> List[Callable]:
    return [
        generate_id,
        validate_email,
        hash_password,
        generate_key,
        drop(["password", "password_verify", "created_by"]),
        # TODO: Fix this by passing it from client & verifying it at server
        default_role(ServiceRole.DATA_SCIENTIST),
    ]


@transform(User, UserView)
def user_to_view_user() -> List[Callable]:
    return [keep(["id", "email", "name", "role", "institution", "website"])]


@serializable()
class UserPrivateKey(SyftObject):
    __canonical_name__ = "UserPrivateKey"
    __version__ = SYFT_OBJECT_VERSION_1

    email: str
    signing_key: SyftSigningKey
    role: ServiceRole


@transform(User, UserPrivateKey)
def user_to_user_verify() -> List[Callable]:
    return [keep(["email", "signing_key", "id", "role"])]
