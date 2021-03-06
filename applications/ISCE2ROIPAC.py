#!/usr/bin/env python3
import isce
from lxml import objectify as OB
from collections import OrderedDict
from datetime import datetime, time
import os
import ConfigParser as CP
import io
from isceobj import Constants as Cn
import numpy as np
import ast

xmlTimeFormat = '%Y-%m-%d %H:%M:%S.%f'
class insarProcXML(object):
    '''
    Read in the metadata files generated by ISCE and create ROI-PAC equivalents.
    '''

    def __init__(self, xmlfile='insarProc.xml'):
        '''Constructor. Not much here.'''
        self.xmlfile = xmlfile
        fin = open(self.xmlfile)
        self.xml = OB.fromstring(fin.read())
        fin.close()

    def raw_rsc(self, key=None, write=False):
        '''Write out the RSC files for Raw data.'''

        if key not in ['reference', 'secondary']:
            raise ValueError('Raw Files can only be written for reference or secondary.')


        rsc = OrderedDict()

        ######Sequence similar to Envisat's raw.rsc file
        rsc['FIRST_FRAME'] = 0

        #####Get Scene time
        root = getattr(self.xml, key)
        frame=root.frame
        sensmid = datetime.strptime(frame.SENSING_MID.text, xmlTimeFormat)
        sensstart = datetime.strptime(frame.SENSING_START.text, xmlTimeFormat)
        sensstop = datetime.strptime(frame.SENSING_STOP.text, xmlTimeFormat)

        rsc['FIRST_FRAME_SCENE_CENTER_TIME'] = sensmid.strftime('%Y%m%d%H%M%S') + '{0:2d}'.format(int(sensmid.microsecond/1000.))

        rsc['FIRST_FRAME_SCENE_CENTER_LINE'] = 0
        rsc['DATE'] = sensmid.strftime('%y%m%d')
        rsc['FIRST_LINE_YEAR'] = sensstart.strftime('%Y')
        rsc['FIRST_LINE_MONTH_OF_YEAR'] = sensstart.strftime('%m')
        rsc['FIRST_LINE_DAY_OF_MONTH'] = sensstart.strftime('%d')
        rsc['FIRST_CENTER_HOUR_OF_DAY'] = sensmid.strftime('%H')
        rsc['FIRST_CENTER_MN_OF_HOUR'] = sensmid.strftime('%M')
        rsc['FIRST_CENTER_S_OF_MN'] = sensmid.strftime('%S')
        rsc['FIRST_CENTER_MS_OF_S'] = int(round(sensmid.microsecond/1000.))

        rsc['PROCESSING_FACILITY'] = frame.PROCESSING_FACILITY.text
        rsc['PROCESSING_SYSTEM'] = frame.PROCESSING_SYSTEM.text
        rsc['PROCESSING_SYSTEM_VERSION'] = frame.PROCESSING_SYSTEM_VERSION.text

        ######Platform information.
        instrument = root.instrument
        platform = "[platform]\n" + instrument.PLATFORM.text
        platform = platform.decode('string_escape')
        temp = CP.RawConfigParser()
        temp.readfp(io.BytesIO(platform))
        rsc['PLATFORM'] = temp.get('platform','Mission')[1:-1]
        rsc['ANTENNA_LENGTH'] = temp.get('platform', 'Antenna Length')[1:-1]
        rsc['ANTENNA_SIDE'] = temp.get('platform', 'Look Direction')[1:-1]

        del temp
        rsc['ORBIT_NUMBER'] = frame.ORBIT_NUMBER.text
        rsc['STARTING_RANGE'] = frame.STARTING_RANGE.text
        rsc['ONE_WAY_DELAY'] = None                       #Undefined
        rsc['RANGE_PIXEL_SIZE'] = Cn.SPEED_OF_LIGHT

        rsc['PRF'] = instrument.PRF.text
        rsc['FILE_LENGTH'] = int(frame.NUMBER_OF_LINES.text)
        rsc['WIDTH'] = int(frame.NUMBER_OF_SAMPLES.text)
        rsc['YMIN'] = 0
        rsc['YMAX'] = rsc['FILE_LENGTH']
        rsc['XMIN'] = 0                         #Assuming no prior header bytes
        rsc['XMAX']= rsc['WIDTH']
        rsc['RANGE_SAMPLING_FREQUENCY'] = instrument.RANGE_SAMPLING_RATE.text

        #####Get planet desciption
        planet = self.xml.planet
        rsc['PLANET_GM'] = planet.GM.text
        rsc['PLANET_SPINRATE'] = planet.SPINRATE.text

        temp = sensstart - datetime.combine(sensstart.date(), time(0))
        rsc['FIRST_LINE_UTC'] = temp.total_seconds()

        temp = sensmid - datetime.combine(sensmid.date(), time(0))
        rsc['CENTER_LINE_UTC'] = temp.total_seconds()

        temp = sensstop - datetime.combine(sensstop.date(), time(0))
        rsc['LAST_LINE_UTC'] = temp.total_seconds()

        root1 = getattr(self.xml.runEstimateHeights, 'CHV_'+key)
        rsc['HEIGHT'] = root1.outputs.HEIGHT.text
        rsc['VELOCITY'] = root1.outputs.VELOCITY.text

        rsc['HEIGHT_DT'] = None             #Undefined
        rsc['LATITUDE'] = None              #Undefined
        rsc['LONGITUDE'] = None            #Undefined
        rsc['EQUATORIAL_RADIUS'] = planet.ellipsoid.SEMIMAJOR_AXIS.text
        rsc['ECCENTRICITY_SQUARED'] = planet.ellipsoid.ECCENTRICITY_SQUARED.text
        rsc['EARTH_RADIUS'] = None
        rsc['FILE_START'] = 1
        rsc['WAVELENGTH'] = instrument.RADAR_WAVELENGTH.text
        rsc['PULSE_LENGTH'] = instrument.RANGE_PULSE_DURATION.text
        rsc['CHIRP_SLOPE'] = instrument.CHIRP_SLOPE.text
        rsc['I_BIAS'] = root.iBias.text
        rsc['Q_BIAS'] = root.qBias.text
        rsc['DOPPLER_RANGE0'] = None
        rsc['DOPPLER_RANGE1'] = None
        rsc['DOPPLER_RANGE2'] = None
        rsc['DOPPLER_RANGE3'] = None
        rsc['SQUINT'] = None    #Could be 0. never used
        rsc['ROI_PAC_VERSION'] = 3

        if write:
            outfilename = root.sensor.OUTPUT + '.rsc'
            fid = open(outfilename, 'w')

            for kk, vv in rsc.iteritems():
                fid.write('{0:<40}   {1:<40}\n'.format(kk,vv))

            fid.close()

        return rsc


    def slc_rsc(self, key=None, raw=None, write=False):
        '''
        Create rsc files for all the interferograms generated by ISCE.
        '''

        if key not in ['reference', 'secondary']:
            raise ValueError('SLC files can only be written for reference or secondary.')

        if raw is None:
            rsc = self.raw_rsc(key=key, write=False)
        else:
            rsc = raw

        root = getattr(self.xml, key)
        rootslc = getattr(self.xml.runFormSLC, key)

        #####Values that have changed.
        rsc['RAW_DATA_RANGE'] = rsc['STARTING_RANGE']
        rsc['STARTING_RANGE'] = rootslc.outputs.STARTING_RANGE.text
        rsc['FILE_LENGTH'] = None     #Needs to be output
        rsc['WIDTH'] = int(rootslc.outputs.SLC_WIDTH.text)
        rsc['XMIN'] = 0
        rsc['XMAX'] = rsc['WIDTH']
        rsc['YMIN'] = 0
        rsc['YMAX'] = None
        rsc['FIRST_LINE_UTC'] = None
        rsc['CENTER_LINE_UTC'] = None
        rsc['LAST_LINE_UTC'] = None
        rsc['HEIGHT'] = rootslc.inputs.SPACECRAFT_HEIGHT.text
        rsc['HEIGHT_DT'] = None
        rsc['VELOCITY'] = rootslc.inputs.BODY_FIXED_VELOCITY.text
        rsc['LATITUDE'] = None
        rsc['LONGITUDE'] = None
        #rsc['HEADING'] = float(self.xml.getpeg.outputs.PEG_HEADING)*180.0/np.pi
        rsc['HEADING'] = None    #Verify the source
        rsc['EARTH_RADIUS'] = rootslc.inputs.PLANET_LOCAL_RADIUS.text
        dop =ast.literal_eval(rootslc.inputs.DOPPLER_CENTROID_COEFFICIENTS.text)
        rsc['DOPPLER_RANGE0'] = dop[0]
        rsc['DOPPLER_RANGE1'] = None     #Check units per meter / per pixel
        rsc['DOPPLER_RANGE2'] = None
        rsc['DOPPLER_RANGE3'] = None

        rsc['DELTA_LINE_UTC'] = None
        rsc['AZIMUTH_PIXEL_SIZE'] = None
        rsc['RANGE_PIXEL_SIZE'] = None
        rsc['RANGE_OFFSET'] = None
        rsc['RLOOKS'] = 1
        rsc['ALOOKS'] = 1
        rsc['PEG_UTC'] = 1
        rsc['HEIGHT_DS'] = None
        rsc['HEIGHT_DDS'] = None
        rsc['CROSSTRACK_POS'] = None
        rsc['CROSSTRACK_POS_DS'] = None
        rsc['CROSSTRACK_POS_DDS'] = None
        rsc['VELOCITY_S'] = None
        rsc['VELOCITY_C'] = None
        rsc['VELOCITY_H'] = None
        rsc['ACCELERATION_S'] = None
        rsc['ACCELERATION_C'] = None
        rsc['ACCELERATION_H'] = None
        rsc['VERT_VELOCITY'] = None
        rsc['VERT_VELOCITY_DS'] = None
        rsc['CROSSTRACK_VELOCITY'] = None
        rsc['CROSSTRACK_VELOCITY_DS'] = None
        rsc['ALONGTRACK_VELOCITY'] = None
        rsc['ALONGTRACK_VELOCITY_DS'] = None
        rsc['PEG_UTC'] = None
        rsc['SQUINT'] = None

        if write:
            outfilename = os.path.splitext(root.sensor.OUTPUT.text)[0]+'.slc.rsc'

            fid = open(outfilename, 'w')

            for kk, vv in rsc.iteritems():
                fid.write('{0:<40}   {1:<40}\n'.format(kk,vv))

            fid.close()







if __name__ == '__main__':
    '''Run the test on input xml file.'''

    converter = insarProcXML()
    reference_raw_rsc = converter.raw_rsc(key='reference', write=True)
    secondary_raw_rsc = converter.raw_rsc(key='secondary', write=True)

    reference_slc_rsc = converter.slc_rsc(raw=reference_raw_rsc, key='reference', write=True)
    secondary_slc_rsc = converter.slc_rsc(raw=secondary_raw_rsc, key='secondary', write=True)
