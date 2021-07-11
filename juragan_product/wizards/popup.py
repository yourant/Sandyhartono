from odoo import api, fields, models, _

class popup_message_wizard(models.TransientModel):
    _name="popup.message.wizard"
    _description = "Message wizard to display warnings, alert ,success messages"      
    
    def get_default(self):
        if self.env.context.get("message",False):
            return self.env.context.get("message")
        return False 
    
    def refresh_form(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        } 

    name=fields.Text(string="Message",readonly=True,default=get_default)