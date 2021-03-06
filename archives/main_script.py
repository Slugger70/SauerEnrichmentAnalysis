"""
functions for implementation of Sauer isotope labeling calculation
"""

import re
import numpy as np
from Function import full_correction_matrix, fractional_labelling

from Class import Record, Labelling


def read_mhunter_csv(infile, verbose=False):
    """
    Reads an input file with isotopic labelling information coming
    directly from Agilent Mass Hunter software

    PARAMS
    ------
    infile: str; The name of the input file

    RETURNS
    -------
    record_list: A list of Class.Record containing isotopic labelling information
    """
    record_list = []
    isotope_list = []
    with open(infile, "r") as fp:
        lines = fp.readlines()
    
    # use regex to parse out the species name
    pattern = r"M\+?\d{1,2} Results"
    for i, word in enumerate(lines[0].replace("\n", "").split(',')):
        m_pattern = re.findall(pattern, word)
        if len(m_pattern) > 0:
            species_name = word.replace(" " + m_pattern[0], "")
            
            test = False
            for record in record_list:
                if record.name == species_name:
                    test = True
                    record.add_record_position(i)
                else:
                    pass
            if test == False: # if we haven't seen this before
                record = Record(species_name)
                record.add_record_position(i)
                record_list.append(record)
                
    name_position = -1

    for i, word in enumerate(lines[1].split(',')):
        if word == "Name":
            name_position = i

    for line in lines[2:]:
        #print line
        words = line.split(',')
        #print words
        if name_position > -1:
            sample_name = words[name_position]
        else:
            sample_name = "NotFound"

        for record in record_list:
            positions = record.get_record_positions()
            isotope_list = []
            for position in positions:
                if verbose:
                    print(record.name, " : ", position, " : ", words[position])
                if words[position] != "":
                    try:
                        isotope_list.append(float(words[position]))
                    except(ValueError):
                        print("Could not convert", words[position])
                else:
                    isotope_list.append(0.0)

            record.add_label_isotope_list(sample_name, isotope_list)

    return record_list


def read_atomic_composition(infile):
    """
    @summary: reads the numbers of each atomic species, and the number
    of labelled carbon atoms for each molecular species

    @param infile: the name of the input file
    @type infile: strType

    @return atomic_composition: A dictionary with the atomic composition
                                of each species
    @type atomic_composition: dictType

    @return N_dict: A dictionary of the number of labelled carbons for each
                    species
    @type N_dict: dictType
    """
    with open(infile, "r") as fp:
        lines = fp.readlines()

    atomic_composition = {}
    N_dict = {}

    for line in lines:
        atomic_dict = {}
        words = line.split(',')

        N_dict[words[0]] = int(words[2])

        for word in words[1].split(' '):
            parts = re.split('(\d+)', word)
            atomic_dict[parts[0].lstrip().strip('\"')] = int(parts[1])
        atomic_composition[words[0].strip('\"')] = atomic_dict

    # get rid of all "s and 's
    for key in N_dict.keys():
        name = re.sub(r'\W+', '', key)
        
    for key in atomic_composition.keys():
        name = re.sub(r'\W+', '', key)
        
    return atomic_composition, N_dict
            

def calculate_labelling(record, N_dict, atomic_dict, verbose=False):
    """
    Calculates percentage labelling based on the method of Sauer et al.

    PARAMS
    ------
    record: a class containing a species name, and m0 to mn values of isotopic contribution. 
    Class.Record
    N_dict:A dictionary of the number of labelled carbons for each species (which is the rank of the mdva matrix), where each key is a sample. 
    atomic_dict: A dictionary with the atomic composition of each species
    verbose: bool; verbosity parameter

    RETURNS
    -------
    results_dict: a dictionary of sample name: labelling % pairs
    """
    
    name = record.get_name()
    species_dict = atomic_dict[name]
    #print species_dict

    N = N_dict[name] + 1
    if verbose:
        print(name, N)
    
    convolved_matrix = full_correction_matrix(species_dict, N, cauchy=True)
    if verbose:
        print(convolved_matrix)
    inverse = convolved_matrix.I
    #print inverse
    results_dict = {}

    #now find ms_matrix
    correction_dict = record.get_background_list()
    for key, value in correction_dict.items():
        #print value
        #for val in value:
            #print float(val)/float(sum(value))
        try:
            ms_matrix = np.matrix(([[float(num)/float(sum(value[0:N]))] \
                                        for num in value[0:N]]))
        except(ZeroDivisionError):
            ms_matrix = np.matrix(([[0.0] for i in range(0,N)]))
        #print 'ms', ms_matrix
        #print 'inverse', inverse
        try:
            mdva = inverse*ms_matrix/(sum(inverse*ms_matrix))[0,0]
            labelling = fractional_labelling(mdva)
        except(ValueError):
            print("Error in record", name)
            print("<br />")
            print("size inverse: " ,inverse.shape[0], inverse.shape[1])
            print("size ms_matrix: ",ms_matrix.shape[0], ms_matrix.shape[1])
            print("<br /> ")
        #print "background\n"
        #print  mdva
        #print "\n"

        # the labeling_mdva_list has the fractional labeling as
        # it's first element, then the labeling into each m channel
        # m0, m1, m2 etc, from the mdva matrix
        
        label_mdva_list = []
        label_mdva_list.append(labelling[0,0])
        for number in mdva:
            label_mdva_list.append(float(number[0,0]))
        results_dict[key + "*"] = label_mdva_list
    
    working_dict = record.get_label_isotope_dict()
    
    #temporary counter
    i = 0

    for key, value in working_dict.items():
        #print value
        #for val in value:
            #print float(val)/float(sum(value))
        try:
            ms_matrix = np.matrix(([[float(num)/float(sum(value[0:N]))] for num in value[0:N]]))
        except(ZeroDivisionError):
            ms_matrix = np.matrix(([[0.0] for i in range(0,N)]))
        #except(TypeError):
        #    print i, num, key, value
        #print ms_matrix
        mdva = inverse*ms_matrix/(sum(inverse*ms_matrix))[0,0]
        #print "main\n"
        #print mdva
        #print "\n"
        labelling = fractional_labelling(mdva)
        #print labelling[0,0]

        label_mdva_list = []
        label_mdva_list.append(labelling[0,0])
        for number in mdva:
            label_mdva_list.append(float(number[0,0]))
        results_dict[key] = label_mdva_list

        i = i+1
        
    return results_dict
