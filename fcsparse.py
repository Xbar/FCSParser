#!/bin/env python
# Adapted from FlowPy 4.0 13.05.20013

import sys
import numpy

class FCSParser:
    def __init__(self, filename):
        self.fileHeaderVer = ''         #FCS version
        self.Params = ''                #Info on parameters
        self.logScale = ''              #If parameter is stored in log
        self.paramsLog = ''             #Use l for log transformed parameters
        self.dataLog = ''               #Transform log data into decimal
        self.fileHeaderCell = ''        #Metadata in the header
        self.dataArray = ''             #Raw data from the file
        self.datam3 = ''
        self.numParams = ''             #Number of parameters in the file
        self.numValues = ''             #Number of cells recorded
        
        with open(filename, 'rb') as fcs_file:
            if fcs_file.read(3) != 'FCS':
                print 'Invalid file format. \nTerminating...\n'
                self.valid = 0
                raise ValueError
                return
            self.valid = 1
            
            if self.valid:
                self.fileHeaderVer = fcs_file.read(7)
                fileHeaderStart = int(fcs_file.read(8))
                fileHeaderEnd = int(fcs_file.read(8))
                
                try:
                    fileDataStart = int(fcs_file.read(8))
                    fileDataEnd = int(fcs_file.read(8))
                except ValueError:
                    fileDataEnd = 0
                    fileDataStart = 0
                    
                try:
                    fileAnalysisStart = int(fcs_file.read(8))
                    fileAnalysisEnd = int(fcs_file.read(8))
                except ValueError:
                    fileAnalysisEnd = 0
                    fileAnalysisStart = 0
                
                fcs_file.seek(fileHeaderStart, 0)
                fileHeaderText = fcs_file.read(fileHeaderEnd - fileHeaderStart + 1)
                #Replace textCell with self.fileHeaderCell
                self.fileHeaderCell = fileHeaderText.split(fileHeaderText[0])
                del self.fileHeaderCell[0]
                if fileDataStart==0:
                    fileDataStart= lookupNumericData(self.fileHeaderCell,'$BEGINDATA')
                if fileDataEnd ==0:
                    fileDataEnd=lookupNumericData(self.fileHeaderCell,'$ENDDATA')
                self.numParams = int(self.lookupNumericData(self.fileHeaderCell, '$PAR'))
                self.numValues = int(self.lookupNumericData(self.fileHeaderCell, '$TOT'))
                byteOrder = self.lookupNumericData(self.fileHeaderCell,'$BYTEORD')#Finds the Byte Order
                paramValsBits= self.lookupNumericData(self.fileHeaderCell,'$P1B')#Finds the number of BIT
                dataType = self.lookupNumericData(self.fileHeaderCell,'$DATATYPE')#Finds the Data Type        
                fcs_file.seek(fileDataStart, 0)#Go to the part of the file where data starts
                dataLength = fileDataEnd - fileDataStart + 1
                dataRaw = fcs_file.read(dataLength)#Read the data.
                self.range_list=[]
                
                if dataType == 'I':#Integer
                    if paramValsBits == '16':
                        castType = numpy.uint16
                        blockLen = 2
                    elif paramValsBits == '32':
                        castType = numpy.uint32
                        blockLen = 4
                    elif paramValsBits == '64':
                        castType = numpy.uint64
                        blockLen = 8
                elif dataType == 'F':#Float 32-bit
                    castType = numpy.float32
                    blockLen = 4
                elif dataType == 'D':#Float 64-bit
                    castType = numpy.float64
                    blockLen = 8
                self.dataArray = self.readBlockData(dataRaw, dataLength, blockLen, byteOrder, castType)
                self.dataArray = numpy.reshape(self.dataArray, (self.numValues * self.numParams, 1))
                self.dataArray = numpy.array(self.dataArray)
                self.dataArray = self.reshape(self.dataArray, self.numParams, self.numValues)
                self.dataArray = numpy.transpose(self.dataArray)
                self.dataArray = self.dataArray[0]
                
                #Parameters
                self.Params=[None] * (self.numParams)
                for i in range(1, self.numParams + 1):
                        self.Params[i - 1] = self.lookupNumericData(self.fileHeaderCell, '$P%dN' % (i))#Different parameters used are found out from the textheader.
                self.Params = numpy.reshape(self.Params, (1, self.numParams))
                self.Params = self.Params[0]
                
                #logarithmic data
                self.logScale = [0] * (self.numParams)
                for i in range(1, self.numParams + 1):
                    try:
                        decade = self.lookupNumericData(self.fileHeaderCell, '$P%dE' % (i))
                    except UnboundLocalError:
                        decade = [0,0]
                        
                    decade = int(decade[0])
                    if decade != 0:
                        Range = int(self.lookupNumericData(self.fileHeaderCell, '$P%dR' % (i)))
                        m = 0
                        self.logScale[i - 1] = 1
                        for j in range(self.numValues):
                            if datatype == 'F' or datatype == 'D':
                                self.dataArray[j][i] = 10 ** self.dataArray[j][i]
                            else:
                                self.dataArray[j][i] = 10 ** (self.dataArray[j][i] * decade / float(Range))
                    
    def getParam(self):
        return self.Params
    
    def getValue(self, param):
        for i in range(self.numParams):
            if self.Params[i] == param:
                return numpy.transpose(self.dataArray)[i]
        return None
    
    def readBlockData(self, rawData, rawLen, blockLen, byteOrder, castType):
        arrayLen = rawLen / blockLen
        resultArray = [''] * arrayLen
        blockEnum = list(range(blockLen))
        if byteOrder != '1,2,3,4':
            blockEnum.reverse()
        rawPointer = 0
        for i in range(arrayLen):
            for j in blockEnum:
                resultArray[i] += rawData[j + rawPointer]
            rawPointer += blockLen
            resultArray[i] = numpy.fromstring(resultArray[i], dtype=castType)#
        return resultArray
            
    def lookupNumericData(self, array, fieldname):#we want to find the element which is after a paritcular element(like'$P1B)in order to find
        num = len(array)#the value of the particular element(like BIT)
        i = 0
        for i in range(0, num):
                if array[i] == fieldname:
                        ans = array[i+1]
                        break
        return ans
                    
                    
    def reshape(self, array1, numParams, numValues):#(reshape an array)
        num = len(array1)
        array = [None] * (numParams)            
        for i in range(0, numParams):
                array[i] = [None] * (numValues)
        j = 0           
        for i in range(0, numValues):
                for k in range(0, numParams):
                        array[k][i] = array1[j]
                        j = j + 1
        return array
