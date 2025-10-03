# indico_payment_voucher/plugin.py

from flask import flash, redirect, request
from flask_pluginengine import current_plugin
from indico.core.plugins import IndicoPlugin
from indico.modules.events.payment import PaymentPluginMixin
from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.util import register_transaction
from indico.modules.events.payment.controllers import RHPaymentBase
from indico.core.plugins import IndicoPluginBlueprint
from indico.web.flask.util import url_for


class VoucherPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """Simple Voucher Payment Plugin"""
    
    configurable = False
    
    default_settings = {
        'method_name': 'Voucher Code'
    }
    
    # Simple hardcoded vouchers for testing
    VALID_VOUCHERS = {
        'VOUCHER123': {'value': 100, 'currency': 'EUR'},
        'VOUCHER456': {'value': 50, 'currency': 'EUR'},
        'TEST2024': {'value': 200, 'currency': 'EUR'}
    }
    
    def get_blueprints(self):
        return IndicoPluginBlueprint('payment_voucher', __name__)
    
    def adjust_payment_form_data(self, data):
        """Add payment route to form data"""
        data['payment_url'] = url_for('.pay', data['registration'].locator)
        return data


class RHVoucherPayment(RHPaymentBase):
    """Handle voucher payment"""
    
    def _process(self):
        if request.method == 'GET':
            # Show payment form
            return current_plugin.render_template(
                'payment_form.html',
                registration=self.registration
            )
        
        # Process payment
        voucher_code = request.form.get('voucher_code', '').strip().upper()
        
        # Validate voucher
        vouchers = current_plugin.VALID_VOUCHERS
        if voucher_code not in vouchers:
            flash('Invalid voucher code', 'error')
            return redirect(request.url)
        
        voucher = vouchers[voucher_code]
        
        # Check if voucher covers the amount
        if voucher['value'] < self.registration.price:
            flash('Voucher value is insufficient', 'error')
            return redirect(request.url)
        
        # Register successful payment
        register_transaction(
            registration=self.registration,
            amount=self.registration.price,
            currency=self.registration.currency,
            action=TransactionAction.complete,
            provider='voucher',
            data={'voucher_code': voucher_code}
        )
        
        flash('Payment successful!', 'success')
        return redirect(url_for('event_registration.display_regform', 
                               self.registration.locator.registrant))


# Create blueprint and add route
blueprint = IndicoPluginBlueprint('payment_voucher', __name__)
blueprint.add_url_rule(
    '/event/<int:event_id>/registrations/<int:reg_form_id>/payment/voucher',
    'pay',
    RHVoucherPayment,
    methods=('GET', 'POST')
)