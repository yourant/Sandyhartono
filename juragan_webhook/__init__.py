# -*- coding: utf-8 -*-
from . import controllers
from . import models

from odoo import fields
from odoo.fields import _schema
from odoo.tools import sql


class BigInteger(fields.Integer):
    column_type = ('int8', 'int8')


class BigMany2one(fields.Many2one):
    column_type = ('int8', 'int8')


class BigMany2many(fields.Many2many):

    def update_db(self, model, columns):
        cr = model._cr
        if not self.manual:
            model.pool.post_init(
                model.env['ir.model.relation']._reflect_relation,
                model, self.relation, self._module)
        if not sql.table_exists(cr, self.relation):
            comodel = model.env[self.comodel_name]
            query = """
                CREATE TABLE "{rel}" ("{id1}" BIGINT NOT NULL,
                                      "{id2}" BIGINT NOT NULL,
                                      UNIQUE("{id1}","{id2}"));
                COMMENT ON TABLE "{rel}" IS %s;
                CREATE INDEX ON "{rel}" ("{id1}");
                CREATE INDEX ON "{rel}" ("{id2}")
            """.format(rel=self.relation, id1=self.column1, id2=self.column2)
            cr.execute(query, ['RELATION BETWEEN %s AND %s' %
                               (model._table, comodel._table)])
            _schema.debug("Create table %r: m2m relation between %r and %r",
                          self.relation, model._table, comodel._table)
            model.pool.post_init(self.update_db_foreign_keys, model)
            return True
