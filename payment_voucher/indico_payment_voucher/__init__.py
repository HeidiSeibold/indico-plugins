from indico.util.i18n import make_bound_gettext

from .plugin import VoucherPaymentPlugin

_ = make_bound_gettext('payment_voucher')

__all__ = ['VoucherPaymentPlugin', '_']
