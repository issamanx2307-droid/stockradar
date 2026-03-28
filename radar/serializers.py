from rest_framework import serializers
from .models import Symbol, PriceDaily, Indicator, Signal, Profile, BusinessProfile, StockTerm, PositionAnalysis
from django.contrib.auth.models import User

class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = "__all__"

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "tier", "line_notify_token", "telegram_chat_id", "max_strategies",
            "is_pro", "picture_url", "login_via_google", "can_use_portfolio",
        ]
        read_only_fields = ["tier", "max_strategies", "is_pro", "picture_url", "login_via_google", "can_use_portfolio"]

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "profile"]


class SymbolSerializer(serializers.ModelSerializer):
    exchange_display = serializers.CharField(source="get_exchange_display", read_only=True)
    class Meta:
        model  = Symbol
        fields = ["id","symbol","name","exchange","exchange_display","sector"]


class PriceDailySerializer(serializers.ModelSerializer):
    class Meta:
        model  = PriceDaily
        fields = ["date","open","high","low","close","volume"]


class IndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Indicator
        fields = [
            "date","rsi","ema20","ema50","ema200",
            "macd","macd_signal","macd_hist",
            "bb_upper","bb_middle","bb_lower",
            "atr14","atr_avg30",
            "adx14","di_plus","di_minus",
            "highest_high_20","lowest_low_20",
            "volume_avg20","volume_avg30",
        ]


class SignalSerializer(serializers.ModelSerializer):
    symbol_code    = serializers.CharField(source="symbol.symbol",  read_only=True)
    symbol_name    = serializers.CharField(source="symbol.name",    read_only=True)
    exchange       = serializers.CharField(source="symbol.exchange", read_only=True)
    signal_display = serializers.CharField(source="get_signal_type_display", read_only=True)
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)

    class Meta:
        model  = Signal
        fields = [
            "id","symbol_code","symbol_name","exchange",
            "signal_type","signal_display",
            "direction","direction_display",
            "score","price",
            "stop_loss","risk_pct",
            "atr_at_signal","adx_at_signal","volume_ratio",
            "filter_volume","filter_volatility","filter_adx",
            "created_at",
        ]


class StockTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTerm
        fields = [
            "term",
            "short_definition",
            "full_definition",
            "category",
            "keywords",
            "is_featured",
            "priority",
            "updated_at",
        ]


class PositionAnalyzeRequestSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    buy_price = serializers.DecimalField(max_digits=18, decimal_places=4)


class PositionAnalysisSerializer(serializers.ModelSerializer):
    symbol_code = serializers.CharField(source="symbol.symbol", read_only=True)
    symbol_name = serializers.CharField(source="symbol.name", read_only=True)

    class Meta:
        model = PositionAnalysis
        fields = [
            "id",
            "symbol_code",
            "symbol_name",
            "buy_price",
            "market_price",
            "pnl_pct",
            "rsi14",
            "ema20",
            "ema50",
            "ema200",
            "adx14",
            "decision",
            "score",
            "confidence",
            "explanation",
            "signals",
            "created_at",
        ]
