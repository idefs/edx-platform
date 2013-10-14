# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Coupon.valid_nb_times'
        db.add_column('coupons_coupon', 'valid_nb_times',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'Coupon.valid_until'
        db.add_column('coupons_coupon', 'valid_until',
                      self.gf('django.db.models.fields.DateTimeField')(null=True),
                      keep_default=False)

        # Adding field 'Coupon.valid_course_id'
        db.add_column('coupons_coupon', 'valid_course_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Coupon.valid_nb_times'
        db.delete_column('coupons_coupon', 'valid_nb_times')

        # Deleting field 'Coupon.valid_until'
        db.delete_column('coupons_coupon', 'valid_until')

        # Deleting field 'Coupon.valid_course_id'
        db.delete_column('coupons_coupon', 'valid_course_id')


    models = {
        'coupons.coupon': {
            'Meta': {'object_name': 'Coupon'},
            'coupon_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'currency': ('django.db.models.fields.CharField', [], {'default': "'usd'", 'max_length': '8'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price_reduction': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'valid_course_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'valid_nb_times': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'valid_until': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        }
    }

    complete_apps = ['coupons']