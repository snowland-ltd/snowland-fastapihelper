"""Unit tests for the auth (identity) package (stdlib unittest)."""
import unittest
from dataclasses import dataclass
from typing import Optional

from snowland_fastapihelper.auth import (
    AbstractBaseUser,
    AbstractUser,
    User,
    VirtualUser,
    get_user_model,
    set_user_model,
)


class TestUser(unittest.TestCase):
    def test_identity_key(self):
        user = User(uuid="u-1", merchant_id="m-1")
        self.assertEqual(user.identity_key, "user:u-1")

    def test_is_identity_contract(self):
        self.assertIsInstance(User(uuid="u-1"), AbstractBaseUser)

    def test_requires_uuid(self):
        with self.assertRaises(ValueError):
            User(uuid="")

    def test_optional_fields_default_to_none(self):
        user = User(uuid="u-1")
        self.assertIsNone(user.username)
        self.assertIsNone(user.tenant_id)
        self.assertIsNone(user.merchant_id)


class TestVirtualUser(unittest.TestCase):
    def test_identity_key(self):
        virtual = VirtualUser(identity_type="phone", identity_value="+86138")
        self.assertEqual(virtual.identity_key, "virtual:phone:+86138")

    def test_is_identity_contract(self):
        self.assertIsInstance(
            VirtualUser(identity_type="email", identity_value="a@b.com"), AbstractBaseUser
        )

    def test_requires_identity(self):
        with self.assertRaises(ValueError):
            VirtualUser(identity_type="phone", identity_value="")

    def test_user_and_virtual_do_not_collide(self):
        user = User(uuid="u-1")
        virtual = VirtualUser(identity_type="phone", identity_value="u-1")
        self.assertNotEqual(user.identity_key, virtual.identity_key)


class TestSwappableUserModel(unittest.TestCase):
    def setUp(self):
        self._original = get_user_model()

    def tearDown(self):
        set_user_model(self._original)

    def test_default_is_user(self):
        self.assertIs(get_user_model(), User)

    def test_set_custom_model(self):
        @dataclass
        class CustomUser(AbstractUser):
            email: Optional[str] = None

        set_user_model(CustomUser)
        self.assertIs(get_user_model(), CustomUser)

        instance = get_user_model()(uuid="u-2", email="a@b.com")
        self.assertEqual(instance.identity_key, "user:u-2")
        self.assertEqual(instance.email, "a@b.com")

    def test_rejects_non_abstract_user(self):
        with self.assertRaises(TypeError):
            set_user_model(VirtualUser)
        with self.assertRaises(TypeError):
            set_user_model(object)


if __name__ == "__main__":
    unittest.main()
