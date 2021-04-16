# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from calendar import monthrange
_logger = logging.getLogger(__name__)

class MiningAnalyzerHourmeter(models.TransientModel):
    _name = 'mining.analyzer.hourmeter'

    @api.model
    def _default_config(self):
        ProductionConfig = self.env['production.config'].sudo()
        production_config = ProductionConfig.search([ ( "active", "=", True ) ]) 
        if not production_config :
            raise UserError(_('Please Set Configuration file') )
        return production_config[0]

    production_config_id = fields.Many2one('production.config', string='Production Config', default=_default_config )

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date(string="End Date", required=True)

    @api.multi
    def action_analyze(self):    
        Vehicle = self.env['fleet.vehicle'].sudo()
        vehicles = Vehicle.search( [ ( "tag_ids", "in", self.production_config_id.hm_vehicle_tag_id.id ) ] )
        message = ""
        for vehicle in vehicles:
            request = ("SELECT 'hourmeter' as code "+', name, vehicle_id, date, start_datetime, start, "end" as end_hour, value, driver_id' +\
                    " FROM production_vehicle_hourmeter_log " +\
                    " WHERE  vehicle_id = "+ str( vehicle.id ) +\
                    " AND date BETWEEN '"+self.start_date+"' AND '"+self.end_date+"' " +\
                    " UNION " +\
                     "SELECT 'losstime' as code "+', name, vehicle_id, date, start_datetime, start, "end" as end_hour, hour as value, driver_id' +\
                    " FROM fleet_vehicle_losstime " +\
                    " WHERE  vehicle_id = "+ str( vehicle.id ) +\
                    " AND date BETWEEN '"+self.start_date+"' AND '"+self.end_date+"' " +\
                    " ORDER BY date asc, start_datetime asc ")
            
            self.env.cr.execute(request)
            
            hourmeter_logs = self.env.cr.dictfetchall()
            for ind in range( len( hourmeter_logs ) ):

                if vehicle.state_id.id != 1 :
                    message += "["+hourmeter_logs[ ind ]['name']+"] ["+vehicle.name+"] not in state Ready For Use \n"

                driver = self.env['res.partner'].sudo().search( [ ( "id", "=", hourmeter_logs[ ind ]['driver_id'] ) ] )
                driver_name = " "
                if driver:
                    driver_name = driver[0].name
                    find_driver = self.env['fleet.driver'].sudo().search( [ ( "partner_id", "=", hourmeter_logs[ ind ]['driver_id'] ) ] )
                    if not find_driver :
                        message += "["+hourmeter_logs[ ind ]['name']+"] ["+driver_name+"] doesn`t register on driver table \n"
                
                if ind == 0 : continue
                if hourmeter_logs[ ind ]['value'] > 20 :
                    message += "["+vehicle.name+"] found anomaly at "+hourmeter_logs[ ind ]['date']+" \n"
                
                # _logger.warning( hourmeter_logs[ ind-1 ]["end_hour"] )
                if round( hourmeter_logs[ ind-1 ]["end_hour"], 2 ) != round( hourmeter_logs[ ind ]['start'], 2 ) :
                    message += "["+vehicle.name+"] "+ hourmeter_logs[ ind-1 ]['code'] +" and "+ hourmeter_logs[ ind ]['code'] +" didn`t match at "+hourmeter_logs[ ind-1 ]['date']+"("+str( hourmeter_logs[ ind-1 ]["end_hour"] )+") to "+hourmeter_logs[ ind ]['date']+"("+str( hourmeter_logs[ ind ]['start'] )+") \n"

            if message != "" :
                message += "\n"
                    

        if message == "" :
            raise UserError(_('It Seems Okay') )
        else :
            raise UserError(_( message ) )
        
        return True    
        

    # @api.multi
    # def action_analyze(self):    
    #     Vehicle = self.env['fleet.vehicle'].sudo()
    #     vehicles = Vehicle.search( [ ( "tag_ids", "in", self.production_config_id.hm_vehicle_tag_id.id ) ] )
    #     message = ""
    #     for vehicle in vehicles:
    #         hourmeter_logs = self.env['production.vehicle.hourmeter.log'].search([ ( 'date', '>=', self.start_date ), ( 'date', '<=', self.end_date ), ( 'vehicle_id', '=', vehicle.id ) ], order="date asc, start_datetime asc")
    #         # for ind, hourmeter_log in enumerate( hourmeter_logs ):
    #         for ind in range( len( hourmeter_logs ) ):
    #             vehicle_state_id = hourmeter_logs[ ind ].vehicle_id.state_id.id
    #             if vehicle_state_id != 1 :
    #                 message += "["+hourmeter_logs[ ind ].name+"] ["+hourmeter_logs[ ind ].vehicle_id.name+"] not in state Ready For Use \n"

    #             driver_name = hourmeter_logs[ ind ].driver_id.name
    #             find_driver = self.env['fleet.driver'].sudo().search( [ ( "partner_id", "=", hourmeter_logs[ ind ].driver_id.id ) ] )
    #             if not find_driver :
    #                 message += "["+hourmeter_logs[ ind ].name+"] ["+driver_name+"] doesn`t register on driver table \n"

    #             if hourmeter_logs[ ind ].value > 20 :
    #                 message += "["+vehicle.name+"] found anomaly at "+hourmeter_logs[ ind ].date+" \n"
    #             if ind == 0 : continue
    #             if round( hourmeter_logs[ ind-1 ].end, 2 ) != round( hourmeter_logs[ ind ].start, 2 ) :
    #                 vehicle_losstimes = self.env['fleet.vehicle.losstime'].search([ ( 'date', '>=', hourmeter_logs[ ind-1 ].date ), ( 'date', '<=', hourmeter_logs[ ind ].date ), ( 'vehicle_id', '=', vehicle.id ) ], order="date asc, start_datetime asc")
    #                 if vehicle_losstimes :
    #                     if round( hourmeter_logs[ ind-1 ].end, 2 ) != round( vehicle_losstimes[0].start, 2 ):
    #                         message += "["+vehicle.name+"] Hourmeter and Losstime didn`t match at "+hourmeter_logs[ ind-1 ].date+"("+str( hourmeter_logs[ ind-1 ].end )+") to "+vehicle_losstimes[0].date+"("+str( vehicle_losstimes[0].start )+") \n"

    #                     for j in range( len( vehicle_losstimes ) -1 ):
    #                         if j == 0 : continue
    #                         if round( vehicle_losstimes[ j-1 ].end, 2 ) != round( vehicle_losstimes[ j ].start, 2 ) :
    #                             message += "["+vehicle.name+"] Losstime didn`t match at "+vehicle_losstimes[ j-1 ].date+"("+str( vehicle_losstimes[ j-1 ].end )+") to "+vehicle_losstimes[ j ].date+"("+str( vehicle_losstimes[ j ].start )+") \n"
                                
    #                     j_end = len( vehicle_losstimes ) - 1
    #                     if round( vehicle_losstimes[ j_end ].end, 2 ) != round( hourmeter_logs[ ind ].start, 2 ) :
    #                         message += "["+vehicle.name+"] Losstime and Hourmeter didn`t match at "+vehicle_losstimes[ j_end ].date+"("+str( vehicle_losstimes[ j_end ].end )+") to "+hourmeter_logs[ ind ].date+"("+str( hourmeter_logs[ ind ].start )+") \n"
                    
    #                 if not vehicle_losstimes :  
    #                     message += "["+vehicle.name+"] Hourmeter didn`t match at "+hourmeter_logs[ ind-1 ].date+"("+str( hourmeter_logs[ ind-1 ].end )+") to "+hourmeter_logs[ ind ].date+"("+str( hourmeter_logs[ ind ].start )+") \n"
            
    #         if message != "" :
    #             message += "\n"
                    

    #     if message == "" :
    #         raise UserError(_('It Seems Okay') )
    #     else :
    #         raise UserError(_( message ) )
        
    #     return True    
        