# indico_payment_voucher/plugin.py

from flask import flash, redirect, request
from flask_pluginengine import current_plugin
from indico.core.plugins import IndicoPlugin
from indico.modules.events.payment import (PaymentPluginMixin, 
                                           PaymentPluginSettingsFormBase,
                                           PaymentEventSettingsFormBase)
from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.util import register_transaction
from indico.modules.events.payment.controllers import RHPaymentBase
from indico.core.plugins import IndicoPluginBlueprint
from indico.web.flask.util import url_for
from indico.web.forms.base import IndicoForm
from wtforms import StringField
from wtforms.validators import DataRequired


class PluginSettingsForm(PaymentPluginSettingsFormBase):
    pass


class EventSettingsForm(PaymentEventSettingsFormBase):
    pass


class VoucherForm(IndicoForm):
    voucher_code = StringField('Voucher Code', [DataRequired()])


# Create blueprint and add route
blueprint = IndicoPluginBlueprint('payment_voucher', __name__)

# Define RH class
class RHVoucherPayment(RHPaymentBase):
    """Handle voucher payment"""
    
    csrf_enabled = True 

    def _process(self):
        # for debugging 
        print("REQUEST METHOD:", request.method)


        form = VoucherForm(request.form if request.method == 'POST' else None)

        if request.method == 'GET':
            # Show payment form
            return current_plugin.render_template(
                'event_payment_form.html',
                registration=self.registration,
                form=form
            )
        
        # POST: validate CSRF + form
        if not form.validate_on_submit():
            flash('Invalid submission (maybe CSRF expired?)', 'error')
            return redirect(request.url)

        voucher_code = form.voucher_code.data.strip().upper()
        vouchers = current_plugin.VALID_VOUCHERS
        
        # Process payment
        voucher_code = request.form.get('voucher_code', '').strip().upper()
        
        # Validate voucher
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


# Register route
blueprint.add_url_rule(
    '/event/<int:event_id>/registrations/<int:reg_form_id>/payment/voucher',
    'pay',
    RHVoucherPayment,
    methods=('GET', 'POST')
)

# Define plugin class and return blueprint
class VoucherPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """Voucher"""
    
    configurable = True
    settings_form = PluginSettingsForm
    event_settings_form = EventSettingsForm
    
    default_settings = {
        'method_name': 'Voucher Code'
    }
    
    default_event_settings = {
        'enabled': True,
        'method_name': 'Voucher Code'
    }
    
    # Simple hardcoded vouchers for testing
    VALID_VOUCHERS = {
        'VOUCHER123': {'value': 100, 'currency': 'EUR'},
        'VOUCHER456': {'value': 50, 'currency': 'EUR'},
        'TEST2024': {'value': 200, 'currency': 'EUR'}
    }
    
    def get_blueprints(self):
        return blueprint
    
    def render_payment_form(self, registration):
        form = VoucherForm()
        return self.render_template(
            'event_payment_form.html',
            registration=registration,
            form=form
        )


    
    def adjust_payment_form_data(self, data):
        """Add payment route to form data"""
        registration = data['registration']
        data['payment_url'] = url_for('plugin_payment_voucher.pay',
                                      event_id=registration.event_id,
                                      reg_form_id=registration.registration_form_id)

        return data
