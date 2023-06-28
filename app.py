# -*- coding: utf-8 -*-

# Sample Flask ZarinPal WebGate with SOAP

__author__ = 'Mohammad Reza Kamalifard, Hamid Feizabadi'
__url__ = 'reyhoonsoft.ir , rsdn.ir'
__license__ = "GPL 2.0 http://www.gnu.org/licenses/gpl-2.0.html"

from flask import Flask, url_for, redirect, request

from suds.client import Client


app = Flask(__name__)

MMERCHANT_ID = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'  # Required
ZARINPAL_WEBSERVICE = 'https://www.zarinpal.com/pg/services/WebGate/wsdl'  # Required
amount = 1000  # Amount will be based on Toman  Required
description = u'تسویه'  # Required



@app.route('/payment', methods=['POST'])
def payment():
    # Get amount from Telegram bot
    amount = request.json['amount']
    
    # Make payment request
    client = Client(ZARINPAL_WEBSERVICE)
    result = client.service.PaymentRequest(MMERCHANT_ID,
                                           amount,
                                           description,
                                           str(url_for('verify', _external=True)))
    
    if result.Status == 100:
        # Payment successful
        return jsonify({'status': 'success', 'authority': result.Authority})
    else:
        # Payment failed
        return jsonify({'status': 'error'})

@app.route('/verify/', methods=['POST'])
def verify():
    # Get payment result from ZarinPal
    client = Client(ZARINPAL_WEBSERVICE)
    result = client.service.PaymentVerification(MMERCHANT_ID,
                                                 request.json['authority'],
                                                 request.json['amount'])
    
    if result.Status == 100:
        # Transaction success
        return jsonify({'status': 'success', 'ref_id': str(result.RefID)})
    elif result.Status == 101:
        # Transaction submitted
        return jsonify({'status': 'submitted'})
    else:
        # Transaction failed
        return jsonify({'status': 'failed', 'error_code': str(result.Status)})


if __name__ == '__main__':
    app.run(debug=True)