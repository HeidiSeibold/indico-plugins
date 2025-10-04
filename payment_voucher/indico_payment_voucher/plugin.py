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
        print("[DEBUG] RHVoucherPayment._process called. Request method:", request.method)

        if request.method == 'GET':
            print("[DEBUG] GET request: rendering payment form.")
            form = VoucherForm()
            return current_plugin.render_template(
                'event_payment_form.html',
                registration=self.registration,
                form=form
            )
        else:
            print("[DEBUG] POST request: processing form submission.")
            form = VoucherForm(request.form)
            if not form.validate_on_submit():
                print("[DEBUG] Form validation failed.")
                flash('Invalid submission (maybe CSRF expired?)', 'error')
                return current_plugin.render_template(
                    'event_payment_form.html',
                    registration=self.registration,
                    form=form
                )

            voucher_code = form.voucher_code.data.strip().upper()
            vouchers = current_plugin.VALID_VOUCHERS

            # Validate voucher
            if voucher_code not in vouchers:
                print(f"[DEBUG] Invalid voucher code: {voucher_code}")
                flash('Invalid voucher code', 'error')
                return current_plugin.render_template(
                    'event_payment_form.html',
                    registration=self.registration,
                    form=form
                )

            print(f"[DEBUG] Voucher code valid: {voucher_code}. Registering transaction.")
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
            print("[DEBUG] Payment successful. Redirecting.")
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
    VALID_VOUCHERS = {'VOUCHER123', 'VOUCHER456', 'TEST2024'}
    
    def get_blueprints(self):
        return blueprint

    def adjust_payment_form_data(self, data):
        """Add payment route to form data"""
        registration = data['registration']
        data['payment_url'] = url_for('plugin_payment_voucher.pay',
                                      event_id=registration.event_id,
                                      reg_form_id=registration.registration_form_id)

        return data
    
    def render_payment_form(self, registration):
        form = VoucherForm()
        return current_plugin.render_template(
            'event_payment_form.html',
            registration=registration,
            form=form
        )
