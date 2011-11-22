'''
Created on 18 oct. 2011

@author: openerp
'''

from osv import osv, fields


class plugin_handler(osv.osv_memory):
    _name = 'plugin.handler'
    
    def _make_url(self, cr, uid, res_id, model, context=None):
        """
            @param id: on which document the message is pushed
            @param model: name of the document linked with the mail
            @return url
        """
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='http://localhost:8069', context=context)
        if base_url:
            base_url += '/?id=%s&model=%s'%(res_id,model)
        return base_url
    
    def is_installed(self, cr, uid):
        return True
    
    def partner_get(self, cr, uid, address_email):
        ids = self.pool.get('res.partner.address').search(cr, uid, [('partner_id', '!=', False), ('email', 'like', address_email)])
        res_id = ids and self.pool.get('res.partner.address').browse(cr, uid, ids[0]).partner_id.id or 0
        url = self._make_url(cr, uid, res_id, 'res.partner')
        return ('res.partner', res_id , url)
    
    def document_get(self, cr, uid, email):
        """
            @param email: email is a standard RFC2822 email message
            @return Dictionary which contain id and the model name of the document linked with the mail
                if no document is found the id = 0
                (model_name, res_id, name_get, url) 
        """
        mail_message_obj = self.pool.get('mail.message')
        model = False
        res_id = 0
        url = False

        msg = mail_message_obj.parse_message(email)
        references = [msg.get('message-id')]
        refs =  msg.get('references',False)
        if refs:
            references.extend(refs.split())
            
        msg_ids = mail_message_obj.search(cr, uid, [('message_id','in',references)])
        if msg_ids:
            msg = mail_message_obj.browse(cr, uid, msg_ids[0])
            res_id = msg.res_id
            model = msg.model
            url = self._make_url(cr, uid, res_id, model)
        return (model,  res_id, url)
        
    def document_type(self, cr, uid, context=None):
        """
            Return the list of available model to push
            res.partner is a special case
            otherwise all model that inherit from mail.thread
            ['res.partner', 'project.issue']
        """
        mail_thread_obj = self.pool.get('mail.thread')
        doc_dict = mail_thread_obj.message_capable_models(cr, uid, context)
        doc_dict['res.partner'] = "Partner"
        return doc_dict.items()

    def list_document_get(self, cr, uid, model, name):
        """
            This function return the result of name_search on the object model
            @param model: the name of the model 
            @param : the name of the document
            @return : the result of name_search a list of tuple 
            [(id, 'name')]
        """
        return self.pool.get(model).name_search(cr,uid,name)
    
    def push_message(self, cr, uid, model, email, res_id=0):
        """
            @param email: email is a standard RFC2822 email message
            @param model: On which model the message is pushed
            @param thread_id: on which document the message is pushed, if thread_id = 0 a new document is created 
            @return Dictionary which contain model , url and resource id.
        """
        mail_message = self.pool.get('mail.message')
        model_obj = self.pool.get(model)
        
        msg = mail_message.parse_message(email)
        message_id = msg.get('message-id')
         
        
        mail_ids = mail_message.search(cr, uid, [('message_id','=',message_id),('res_id','=',res_id),('model','=',model)])
        if message_id and mail_ids :
            mail_record = mail_message.browse(cr, uid, mail_ids)[0]
            res_id = mail_record.res_id
            notify = "Email already pushed"
        elif res_id == 0:
            if model == 'res.partner':
                notify = 'User the button Partner to create a new partner'
            else:
                res_id = model_obj.message_new(cr, uid, msg)
                notify = "Mail succefully pushed, a new %s has been created " % model
        else:
            model_obj.message_append_dict(cr, uid, [res_id], msg)
            notify = "Mail succefully pushed"
        url = self._make_url(cr, uid, res_id, model)
        return (model, res_id, url, notify)
        
    
    def contact_create(self, cr, uid, data, partner_id):
        """
            @param data : the data use to create the res.partner.address
                [('field_name', value)], field name is required
            @param partner_id : On which partner the address is attached 
             if partner_id = 0 then create a new partner with the same name that the address
            @return : the partner_id sended or created, this allow the plugin to open the right partner page
        """
        print "create contact", data, partner_id
        partner_obj = self.pool.get('res.partner')
        dictcreate = dict(data) 
        if partner_id == 0:
            partner_id =  partner_obj.create(cr, uid, {'name':dictcreate.get('name')})
        dictcreate['partner_id'] = partner_id
        self.pool.get('res.partner.address').create(cr, uid, dictcreate)
        url = self._make_url(cr, uid, partner_id, 'res.partner')
        return ('res.partner', partner_id, url)
    
    
    
    ##############################
    #                            #
    #    Specific to outlook     #
    #                            #
    ##############################
    
    def attachment_create(self,cr, uid, data):
        """
            @param data : the data use to create the ir.attachment
            [('field_name', value)], field name is required.
        """
        ir_attachment_obj = self.pool.get('ir.attachment')
        attachment_ids = ir_attachment_obj.search(cr, uid, [('res_model', '=', data.get('res_model')), ('res_id', '=', data.get('res_id')), ('datas_fname', '=', data.get('datas_fname'))])
        if attachment_ids:
            return attachment_ids[0]
        else:
            vals = {"res_model": data.get('res_model'), "res_id": data.get('res_id'), "name": data.get('name'), "datas" : data.get('datas'), "datas_fname" : data.get('datas_fname')}
            return ir_attachment_obj.create(cr, uid, vals)

