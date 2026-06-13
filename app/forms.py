"""WTForms definitions.

Using WTForms gives us two things for free: server-side validation of every
field (length, type, required, range) and CSRF tokens on every POST. Combined
with the SQLAlchemy ORM (parameterised queries) and Jinja2 autoescaping, this
closes the common injection and tampering paths.
"""
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    FieldList,
    FormField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
)

from .models import RISK_LEVELS, STATUSES


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])


class RegisterForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    passport_no = StringField("Passport number", validators=[Optional(), Length(max=40)])
    nationality = StringField("Nationality", validators=[Optional(), Length(max=60)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )


class ItemForm(FlaskForm):
    # Used as a subform; CSRF handled by the parent form.
    class Meta:
        csrf = False

    description = StringField("Description", validators=[Optional(), Length(max=160)])
    category = SelectField(
        "Category",
        choices=[
            ("electronics", "Electronics"),
            ("apparel", "Apparel"),
            ("food", "Food and agriculture"),
            ("medical", "Medical and pharmaceutical"),
            ("commercial", "Commercial goods"),
            ("currency", "Currency and valuables"),
            ("general", "General"),
        ],
        default="general",
    )
    quantity = IntegerField("Qty", validators=[Optional(), NumberRange(min=1, max=100000)], default=1)
    unit_value = DecimalField(
        "Unit value", validators=[Optional(), NumberRange(min=0, max=100000000)], default=0, places=2
    )


class DeclarationForm(FlaskForm):
    flight_id = SelectField("Arriving flight", coerce=int, validators=[DataRequired()])
    currency = SelectField(
        "Currency",
        choices=[("USD", "USD"), ("EUR", "EUR"), ("GBP", "GBP"), ("UGX", "UGX")],
        default="USD",
    )
    has_goods_to_declare = BooleanField("I have goods to declare", default=True)
    traveler_note = TextAreaField("Notes for the inspector", validators=[Optional(), Length(max=500)])
    items = FieldList(FormField(ItemForm), min_entries=3, max_entries=12)


class ReviewForm(FlaskForm):
    decision = SelectField(
        "Decision",
        choices=[
            ("cleared", "Clear declaration"),
            ("flagged", "Flag for follow up"),
            ("inspected", "Mark as physically inspected"),
        ],
        validators=[DataRequired()],
    )
    risk_level = SelectField(
        "Risk level", choices=[(r, r.title()) for r in RISK_LEVELS], validators=[DataRequired()]
    )
    inspector_note = TextAreaField("Inspector note", validators=[Optional(), Length(max=500)])


class FlightForm(FlaskForm):
    flight_number = StringField("Flight number", validators=[DataRequired(), Length(max=12)])
    airline = StringField("Airline", validators=[DataRequired(), Length(max=80)])
    origin = StringField("Origin city", validators=[DataRequired(), Length(max=80)])
    origin_code = StringField("Origin code", validators=[Optional(), Length(max=6)])
    scheduled_arrival = StringField(
        "Scheduled arrival", validators=[DataRequired(), Length(max=20)]
    )


class UserAdminForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField(
        "Role",
        choices=[("traveler", "Traveler"), ("inspector", "Customs Inspector"), ("admin", "Supervisor")],
        validators=[DataRequired()],
    )
    password = PasswordField("Password", validators=[Optional(), Length(min=8, max=128)])
    is_active = BooleanField("Active", default=True)
