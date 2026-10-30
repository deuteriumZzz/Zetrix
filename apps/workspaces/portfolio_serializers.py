"""Bounded USD input contracts shared by manual entry and CSV parsing."""
from decimal import Decimal
import re
from rest_framework import serializers
from .serializers import StrictSerializer

MAX_ROWS = 1000
MAX_BYTES = 2 * 1024 * 1024
CSV_COLUMNS = ('supplier', 'country_code', 'category', 'monthly_cost', 'currency')


class PlainText(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError('Use text.')
        value = super().to_internal_value(data)
        if value.lstrip().startswith(('=', '+', '-', '@')):
            raise serializers.ValidationError('Spreadsheet formula prefixes are not allowed.')
        if any(ord(char) < 32 and char not in '\n\r\t' for char in value):
            raise serializers.ValidationError('Unsupported control character.')
        return value


class MoneyString(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str) or not re.fullmatch(r'[0-9]{1,10}(?:\.[0-9]{1,2})?', data):
            raise serializers.ValidationError('Use a plain decimal string with at most two decimal places.')
        amount = Decimal(data)
        if not Decimal(1) <= amount <= Decimal(10**9):
            raise serializers.ValidationError('Monthly cost must be between 1 and 1000000000 USD.')
        return format(amount, '.2f')


class PortfolioLineInput(StrictSerializer):
    supplier = PlainText(max_length=160)
    country_code = serializers.RegexField(r'\A[A-Z]{2}\Z', max_length=2)
    category = PlainText(max_length=120)
    monthly_cost = MoneyString(max_length=13)
    currency = serializers.ChoiceField(choices=['USD'])


class PortfolioInput(StrictSerializer):
    lines = serializers.ListField(child=PortfolioLineInput(), min_length=1, max_length=MAX_ROWS)

    def validate_lines(self, value):
        if sum(Decimal(line['monthly_cost']) for line in value) > Decimal(10**9):
            raise serializers.ValidationError('Portfolio monthly total must not exceed 1000000000 USD.')
        return value


class CSVPreviewInput(StrictSerializer):
    csv = serializers.CharField(max_length=MAX_BYTES, trim_whitespace=False)

    def validate_csv(self, value):
        try:
            size = len(value.encode('utf-8'))
        except UnicodeEncodeError as exc:
            raise serializers.ValidationError('CSV must contain valid UTF-8 text.') from exc
        if size > MAX_BYTES:
            raise serializers.ValidationError('CSV exceeds 2 MiB.')
        return value


class ConfirmInput(StrictSerializer):
    pass
