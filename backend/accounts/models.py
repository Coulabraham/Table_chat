from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, public_id, display_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Une adresse email est requise.")
        user = self.model(
            email=self.normalize_email(email).lower(),
            public_id=public_id.lower(),
            display_name=display_name,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, public_id, display_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, public_id, display_name, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    public_id = models.CharField(max_length=32, unique=True, db_index=True)
    display_name = models.CharField(max_length=80)
    bio = models.CharField(max_length=160, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["public_id", "display_name"]
    objects = UserManager()

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email).lower()
        self.public_id = self.public_id.lower()
        super().save(*args, **kwargs)
