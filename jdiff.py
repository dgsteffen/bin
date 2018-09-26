#!/usr/bin/env python
import sys
import json
import random

# some comparison function objects

"""
Functions and classes for comparing json dictionaries.  The heavy lifting
for correct type dispatch and recursion is done by the comparitor class.
"""

def built_in_equal(a, b, ignored=None):
    """Compares a to b using built in equality operator.  Return None if a and
    b are equal returns pair containing two values if not equal."""

    return (a, b) if a != b else None

class float_compare_rel_diff:
    """A function object that compares floating point numbers for equality using
    relative difference. 
    a~=b if abs(a-b)/(a==0 ? 1 : abs(a)) <= threshold
    """

    def __init__(self, thresh = 0):
        self.thresh = float(thresh)
        self.max_rel_diff = None

    def __call__(self, a, b):
        try :
            d = abs(a) if a != 0.0 else 1.0
            rd = abs(a-b)/d
            self.max_rel_diff = max(self.max_rel_diff, rd) if self.max_rel_diff != None else rd
            return (a,b) if rd > self.thresh else None
        except :
            print "YO!", a, b
            sys.exit(1)


def list_compare_equality(a, b, comp):
    """Recursively compare elements in lists a and b.  Uses comp to compare
    each element.  Return None if the lists are equal, otherwise return
    a dictionary keyed on element index with the value pairs as value."""

    al = len(a)
    bl = len(b)
    d = {}
    # loop over longer of the two lists
    for i in range(0, max(al, bl)):
        tag = 'index ' + str(i)
        # no index i for a difference is ('', b[i])
        if i >= al:
            d[tag] = ('',b[i])
            continue
        # no index i for b difference is (a[i], '')
        if i >= bl:
            d[tag] = (a[i], '')
            continue

        if type(a[i]) != type(b[i]):
            #differences[k] = (a[i], b[i])
            d[tag] = b[i]
            continue

        # use comparitor to compare the two elements
        # note if the elements are lists comp will need
        # to recurse back to this function for those.
 
        cmpres = comp.cmp(a[i], b[i])
        # if there was a difference add to dictionary
        if cmpres != None:
            d[tag] = cmpres

    # return None of there were no differeneces otherwise return the difference
    # map
    return d if len(d) else None

class comparitor:
    """comparitor is a function object that can compare two json dictionaries
    for equality.  It uses 3 function object subordinates to do this:
    - float_compare: for comparing floating point numbers.
    - list_compare: for comparing lists.
    - default_compare: for comparing all other types.
    Note that dictionary is not in this list.  comparitor itself is the function
    object for comparing dictionaries.
    """

    def __init__(self,
                 float_compare = float_compare_rel_diff(),
                 list_compare = built_in_equal,
                 default_compare = built_in_equal):
        """Create an instance with the specified function object subordinates.
        """

        self.fc = float_compare
        self.lc = list_compare
        self.default = default_compare

    def cmp(self, a, b):
        """Dispatches comparison of a and b to the appropriate subordinate
        function object."""

        new_diffs = None

        if isinstance(a, float): # dispatch to the floating point comparison
            new_diffs = self.fc(a, b)
        elif isinstance(a, list): # dispatch to the list comparison
            new_diffs = self.lc(a, b, self)
        elif isinstance(a, dict): # dispatch to the dictionary comparison (me)
            new_diffs = self(a, b)
        else: # all other types use the default
            new_diffs = self.default(a, b)

        return new_diffs

    def max_floating_point_relative_difference(self):

        res = None
        try:
            res = self.fc.max_rel_diff
        except:
            pass
        return res


    def __call__(self, a, b):
        """Recursively compare two json dictionaries for equality.  Returns a
        dictionary of differences or None if there were no differences.
        """

        # get the keys
        a_keys = set(a.keys())
        b_keys = set(b.keys())

        # dictionary of differences
        differences = {}

        # for keys in a but not in b
        for k in a_keys - b_keys:
            differences[k] = (a[k], '')

        # for keys in b but not in a
        for k in b_keys - a_keys:
            differences[k] = ('', b[k])

        # key is in both dictionaries
        for k in a_keys & b_keys:
            av = a[k]
            bv = b[k]
            # if types are different put in differenece dictionary
            if type(av) != type(bv):
                differences[k] = (av, bv)
                continue

            # dispatch comparison
            new_diffs = self.cmp(av, bv)

            # if there were diffs record
            if new_diffs != None:
                differences[k] = new_diffs

        # return the dictionary of differences if there were any or None if
        # there weren't
        return differences if len(differences) else None

def apply_differences(mod, diffs):

    if isinstance(mod, dict):
      if isinstance(diffs, tuple):
        mod = diffs[1]
      elif isinstance(diffs, dict):
        for k,v in diffs.iteritems():
          if not mod.has_key(k):
            mod[k] = v[1]
          else:
            if isinstance(v, tuple):
              if v[1] == '':
                del mod[k]
              else:
                mod[k] = apply_differences(mod[k], v)
            else:
              mod[k] = apply_differences(mod[k], v)
      else:
        raise Exception("Uh Oh")

    elif isinstance(mod, list):
      deletes=[]
      for k,v in diffs.iteritems():
        intk = int(k.replace("index ",""))
        if isinstance(v, tuple):
          if v[0] == '':#was not in a, add it
            mod.append(v[1])
          elif v[1] == '':#was not in b, del it
            #del mod[intk]
            deletes += [intk]
          else:#was in both, but changed
            mod[intk] = v[1]
        else:
          mod[intk] = apply_differences(mod[intk], v)#v is a dict
      deletes.sort()
      deletes.reverse()
      for d in deletes:
        del mod[d]
    else:
      if isinstance(diffs, tuple):
        mod = diffs[1] #the b in (a,b)
      else:
        mod = diffs

    return mod

# convience

def compare_json_data(a, b, comp):
    """Convience function to compare 2 arrays of json dictionaries.  It is
    really a wrapper around a loop over a comparitor instance that:
    - takes care of different sized arrays
    - creates a dictionary with line numbers containing differeneces as the key
    - Counts total number of lines that differed.
    
    Returns a pair.  The first element is the number of lines that
    differed.  The second selement is a dictionary of differences.
    """

    al = len(a)
    bl = len(b)

    differences = {}

    n_diffs = 0

    # loop over the longer of the two arrays
    for i in range(0, max(al, bl)):
        # get the data.  If out of range of either
        # get an empty dictionary.  The comparitor
        # can deal with this
        a_data = {} if i >= al else a[i]
        b_data = {} if i >= bl else b[i]

        # compare
        this_diff = comp(a_data, b_data)

        # if there were differences record in dictionary and increment
        # line difference count
        if this_diff != None:
            n_diffs += 1
            differences['line ' + str(i+1)] = this_diff

    return (n_diffs, differences)

def get_json(file):
    """Read a file and create an array of json dictionaries."""

    try:
        f = open(file, 'r')
        raw_data = f.readlines()
        f.close()
    except:
        print 'Could not read data in ' + file
        sys.exit(1)

    j = []
    decoder = json.JSONDecoder()

    i = 0
    for line in raw_data :
        line = line.rstrip()
        if len(line) == 0 :
            continue
        try :
            j.append(decoder.decode(line))
        except:
            print "Error decoding line", i, "of file", file
            sys.exit(1)
        i += 1

    return j

# generic script support (version, help, about ...)

def version_str():
    """Create a version number string."""

    return str(random.random())

def about():
    """Print about information and exit."""

    import os
    import os.path
    print os.path.basename(sys.argv[0])
    print 'Version ' + version_str()
    print 'Written by Sean Roberts <sean.roberts@numerica.us>'
    print 'Numerica Corporation 2011'
    sys.exit(0)

def version():
    """Print version number and exit."""
    print version_str()
    sys.exit(0)

def usage():
    """Print help information and exit."""

    import os
    import os.path

    prog = os.path.basename(sys.argv[0])

    usage_txt = """
NAME
    """ + prog + """ - Compare two json message files

SYNOPSIS
    """ + prog + """ [-t | --float-threshold <threshold>]
          [-d | --show-max-rel-diff]
          [--diff-tool <diff tool>]
          [--test] [--tests=<test numbers>]
          [-v | --verbose] [-h | --help] [--about] [--version]
          <canon file> <comparison file>

DESCRIPTION
    """ + prog + """ compares two json message files for equality.  It can
    recursively follow the json dictionary for each message pair (line by line)
    and check for equality (equality can be thresholded for floating point
    comparisons - see --float-threshold).  This alleviates the problems with
    json dictionary ordering as well as the general problem of floating point
    comparisons.

OPTIONS
    -t, --float-threshold <threshold>
        Floating point threshold for floating point comparison.  If this is not
        specified or is <= 0 floating point numbers will be compared based on
        equality.  If > 0 comparison is done using relative difference: a~=b
        if abs(a-b)/(a==0 ? 1 : abs(a)) <= threshold

    -d, --show-max-rel-diff
        When set the maximum floating point relative difference will be written
        to standard output.

    --diff-tool=<diff tool>
        """ + prog + """ will run your favorite diff program with a pretty-printed
        output format after completing its comparison of the json files.  
        For example, you could visualize the diffs in kdiff (--diff-tool=kdiff), 
        or gvim (--diff-tool="gvim -d"), or any other diff program that accepts
        two command line arguments to diff.

    --test
        Run unit tests

    --tests=<test numbers>
        Run the specified set of comma separated unit tests

    -v, --verbose
       Be verbose.  Namely this will cause """ + prog + """ to output the diffs
       (see OUTPUT).

    -h, --help
        Print the help information (your looking at it now) and exit.

    --about
        Print the about information and exit.

    --version
        Print the version and exit.

OUTPUT
    """ + prog + """ returns the number of lines that differed between the files
    to the calling process ($?).  If -v is specified """ + prog + """ will also
    write the diffs in json format to standard output.  This format is a
    dictionary of line number to a dictionary of entry differences.  The entry
    differences are in turn a dictionary of keys for which a difference existed
    to a pair containing the values from each file.  An empty value indicates
    the fields was not present in that file.  In addition the output for field
    differences for lists is a dictionary of element index (0 based) to field
    difference pairs.

    For example (note: in this example the output has been reformatted for
    readability """ + prog + """ outputs the json in condensed format - all
    one line)

    { 
      "line 2" : 
      { 
        "int_key" : [ 2, 12 ]
      },

      "line 4" : 
      { 
        "int_list" : 
        { 
          "index 2" : [ 3, 13 ]
        },
        "list_list" : 
        { 
          "index 1" : 
          { 
            "index 2" : [ 13, 113 ]
          }
        }
      }
    }

    On line 2 the field with key "int_key" was different - 2 in the first file
    12 in the second.

    Line 4 contained some lists.  The "int_list" field differed in index 2 - 3
    in the first file, 13 in the second.  Line 4 also contained a list of lists
    that differed.  In this case the 1,2 element differed.

AUTHOR
    Written by Sean Roberts <sean.roberts@numerica.us>
    Diff tool functionality added by Nick Parrish <nick.parrish@numerica.us>
"""
    print usage_txt
    sys.exit(0)

def test(test_nos, comp, verbose, indent_level=None):
    """Unit tests"""
    # TODO unit tests - add more, indicate pass/fail

    class test_case:

        def __init__(self, canon, comparisons, description):
            jd = json.JSONDecoder()
            self.canon = []
            for i in canon:
                self.canon.append(jd.decode(i))

            self.comparisons = {}
            for i,d in comparisons.iteritems():
                this_comp = []
                for l in d['data']:
                    this_comp.append(jd.decode(l))
                self.comparisons[i] = {'data':this_comp,
                                       'description':d['description'],
                                       'expected':jd.decode(d['expected'])}

            self.comp = comp

            self.description = description

        def __call__(self):
            encoder = json.JSONEncoder(indent=indent_level)

            if verbose:
                print 'Canonical:\n  data: ' + encoder.encode(self.canon)

            full_pass = True
            for i,d in self.comparisons.iteritems():
                data = d['data']
                if verbose:
                    print '\n  Comparison', str(i) + ':', d['description']
                    print '  data:', encoder.encode(data)
                diff = compare_json_data(self.canon, data, self.comp)
                if diff[0]:
                    comp_res = self.comp(json.JSONDecoder().decode(encoder.encode(diff[1])), d['expected'])
                else:
                    comp_res = self.comp({},d['expected'])

                passed = comp_res == None

                full_pass = full_pass and passed

                if verbose:
                    print '  result  : ' + encoder.encode(diff[1])
                    print '  expected: ' + encoder.encode(d['expected'])
                    print '  passed? ', passed

            return full_pass

    tests = {}

    tests[0] = test_case(['{"key":1}'],
                         {1:{'data':['{"key":1}'],
                             'description':'Equal',
                             'expected':'{}'}
                          },
                         'Equality test')

    tests[1] = test_case(['{"int_key":1}'],
                         {1:{'data':['{"int_key":2}'],
                             'description':'Value different',
                             'expected':'{"line 1":{"int_key":[1,2]}}'},
                          2:{'data':['{"string_key":"string_value"}'],
                             'description':'Keys different',
                             'expected':'{"line 1":{"string_key":["","string_value"],"int_key":[1,""]}}'}
                          },
                         'basic value difference')

    tests[2] = test_case(['{"string_key":"string_value1","int_key": 1}',
                          '{"string_key":"string_value2","int_key": 2}',
                          '{"string_key":"string_value3","int_key": 3}'],
                         {1:{'data':['{"string_key":"string_value1","int_key":1}',
                                     '{"string_key":"string_value2","int_key":2}'],
                             'description':'Fewer comparison lines',
                             'expected':'{"line 3":{"string_key":["string_value3",""],"int_key":[3,""]}}'},
                          2:{'data':['{"string_key":"string_value1","int_key":1}',
                                     '{"string_key":"string_value2","int_key":2}',
                                     '{"string_key":"string_value3","int_key":3}',
                                     '{"string_key":"string_value4","int_key":4}'],
                             'description':'More comparison lines',
                             'expected':'{"line 4":{"string_key":["","string_value4"],"int_key":["",4]}}'}
                          },
                         'Multi line test')

    tests[3] = test_case(['{"list_key":[1,2,3,4]}'],
                         {1:{'data':['{"list_key":[1.0,2,3,4]}'],
                             'description':'Float/int value equivalence',
                             'expected':'{}'},
                         2:{'data':['{"list_key":[1,2,3,5]}'],
                            'description':'Value different',
                            'expected':'{"line 1":{"list_key":{"index 3":[4,5]}}}'},
                         3:{'data':['{"list_key":[1,2,3,4,5]}'],
                             'description':'Comparison list longer',
                             'expected':'{"line 1":{"list_key":{"index 4":["",5]}}}'},
                         4:{'data':['{"list_key":[1,2,3]}'],
                             'description':'Comparison list shorter',
                             'expected':'{"line 1":{"list_key":{"index 3":[4,""]}}}'}
                          },
                         'Basic list tests')

    tests[4] = test_case(['{"float_key":3.14}'],
                         {1:{'data':['{"float_key":2.8}'],
                             'description':'Floating point value different',
                             'expected':'{"line 1": {"float_key": [3.1400000000000001, 2.7999999999999998]}}'},
                          2:{'data':['{"float_key":3.140000000000001}'],
                             'description':'Floating point close (pass depends on threshold)',
                             'expected':'{}'}
                          },
                         'Simple floating point comparison test')

    tests[5] = test_case(['{"zero":0.0}'],
                         {1:{'data':['{"zero":0.0}'],
                             'description':'Comparison exactly zero',
                             'expected':'{}'},
                          2:{'data':['{"zero":0.0001}'],
                             'description':'Comparison 0.0001 (pass depends on threshold)',
                             'expected':'{}'},
                          3:{'data':['{"zero":0.0000000000000000001}'],
                             'description':'Comparison very small (pass depends on threshold)',
                             'expected':'{}'}
                          },
                         'Floating point near zero test')

    tests[6] = test_case(['{"top_int_key":1,"sub1":{"sub1_int_key":2,"sub2":{"sub2_int_key":3}}}'],
                         {1:{'data':['{"top_int_key":11,"sub1":{"sub1_int_key":2,"sub2":{"sub2_int_key":3}}}'],
                             'description':'Value at top different',
                             'expected':'{"line 1":{"top_int_key":[1,11]}}'},
                          2:{'data':['{"top_int_key":1,"sub1":{"sub1_int_key":12,"sub2":{"sub2_int_key":3}}}'],
                             'description':'Value in subsection 1 different',
                             'expected':'{"line 1": {"sub1": {"sub1_int_key": [2, 12]}}}'},
                          3:{'data':['{"top_int_key":1,"sub1":{"sub1_int_key":2,"sub2":{"sub2_int_key":13}}}'],
                             'description':'Value in subsection 2 different',
                             'expected':'{"line 1": {"sub1": {"sub2": {"sub2_int_key": [3, 13]}}}}'}
                          },
                         'Subsection tests')

    tests[7] = test_case(['{"int_list":[1,2,3,4],"float_list":[1.0,2.0,3.0,4.0],"string_list":["s1","s1","s3"],"list_list":[[1,2,3,4],[11,12,13,14],[21,22,23,24]]}'],
                         {1:{'data':['{"int_list":[1,2,3,5],"float_list":[1.0,2.0,3.0,4.0],"string_list":["s1","s1","s3"],"list_list":[[1,2,3,4],[11,12,13,14],[21,22,23,24]]}'],
                             'description':'Int list value different',
                             'expected':'{"line 1":{"int_list":{"index 3":[4,5]}}}'},
                          2:{'data':['{"int_list":[1,2,3,4],"float_list":[1.0,2.0,3.2,5.0],"string_list":["s1","s1","s3"],"list_list":[[1,2,3,4],[11,12,13,14],[21,22,23,24]]}'],
                             'description':'Float list value different',
                             'expected':'{"line 1":{"float_list":{"index 3":[4.0,5.0],"index 2":[3.0,3.2000000000000002]}}}'}, 
                          3:{'data':['{"int_list":[1,2,3,4],"float_list":[1.0,2.0,3.0,4.0],"string_list":["s1","s1","s4"],"list_list":[[1,2,3,4],[11,12,13,14],[21,22,23,24]]}'],
                             'description':'String list value different',
                             'expected':'{"line 1":{"string_list":{"index 2":["s3","s4"]}}}'},
                          4:{'data':['{"int_list":[1,2,3,4],"float_list":[1.0,2.0,3.0,4.0],"string_list":["s1","s1","s3"],"list_list":[[1,2,3,4],[11,12,113,14],[21,22,23,124]]}'],
                             'description':'list list values different',
                             'expected':'{"line 1": {"list_list": {"index 2": {"index 3": [24, 124]}, "index 1": {"index 2": [13, 113]}}}}'}
                          },
                         'Advanced list test')

    if len(test_nos) == 0:
        test_nos = tests.keys()

    full_pass = True
    for i in test_nos:
        if tests.has_key(i):
            if verbose:
                print
                print 'test', str(i) + ':', tests[i].description
            passed = tests[i]()
            if verbose:
                print 'passed test', str(i) + '?', passed
            full_pass = full_pass and passed

    if verbose:
        if full_pass:
            print 'Passed',
        else:
            print 'Failed',
        print 'unit tests'
    sys.exit(not full_pass)

# here is main
if __name__ == "__main__":
    import getopt

    try:
        (opts, args) = getopt.gnu_getopt(sys.argv, 't:dvh',
                                         ['float-threshold','diff-tool=',
                                          'lenient-end','show-max-rel-diff',
                                          'test','tests=','test-indent=',
                                          'verbose', 'help','about','version'])
                                      

    except getopt.GetoptError, err:
        print 'Bad argument: ' + str(err)
        sys.exit(1)

    verbose=0
    float_thresh = 0.0
    print_max_rel_diff = False
    diff_tool = None
    lenient_end = False
    run_test = False
    tests = []
    test_indent_level = None

    for o,a in opts:
        if o == '--test':
            run_test = True
        elif o == '--tests':
            tests += [int(i) for i in a.split(',')]
        elif o in ('-t', '--float-threshold'):
            float_thresh = float(a)
        elif o in ('-d', '--show-max-rel-diff'):
            print_max_rel_diff = True
        elif o in ('--diff-tool'):
            diff_tool = a
        elif o in ('--lenient-end'):
            lenient_end = True
        elif o == '--test-indent':
            test_indent_level = int(a)
        elif o in ('-v', '--verbose'):
            verbose += 1
        elif o in ('-h', '--help'):
            usage()
        elif o == '--about':
            about()
        elif o == '--version':
            version()

    if len(tests):
        run_test = True

    if diff_tool != None:
        try:
            import JsonStruct
        except:
            print "JsonStruct not found (needed for diff-tool), PNUTS should be on your PYTHONPATH!"
            sys.exit(1)

    # set up the comparitor.
    fc = float_compare_rel_diff(float_thresh)

    c = comparitor(float_compare = fc, list_compare = list_compare_equality)

    # if we were asked to run unit tests do so.
    if run_test:
        #a = """{ "a":"1", "z":1.0000001, "c":"b", "d":[0,1,2,3], "e":"", "g":{"g1":""}, "z1":{},        "j":[0,1,2,3,4,5], "j2":[1,2,3], "k":100, "n":[{"2":1.000002},{"1":{}}] }"""
        #b = """{ "a":"1", "z":1.0010001, "c":"c", "d":[0,1,2,3], "f":"", "h":{"g1":""}, "z1":{"i":[1]}, "j":[1,2,3], "j2":[0,1,2,3,4,5], "k":"1", "n":[{"2":1.000001}]          }"""
        #decoder = json.JSONDecoder()
        #a = decoder.decode(a)
        #b = decoder.decode(b)
        #d = compare_json_data([a],[b],c)
        #if d[0]:
        #  print "DIFF"
        #  for index in d[1]:
        #    from copy import deepcopy
        #    d_data = apply_differences(deepcopy(a), d[1][index])
        #    print "B: ",json.JSONEncoder(sort_keys=True).encode(b)
        #    print "A: ",json.JSONEncoder(sort_keys=True).encode(a)
        #    print "   ",json.JSONEncoder(sort_keys=True).encode(d_data)
        #else:
        #  print "NO DIFF"
        #sys.exit(0)
        test(tests, c, verbose, test_indent_level)

    # check that we have at least 2 files to diff
    # args[0] is the program name
    if len(args) != 3:
        print 'Not enough files specified'
        usage()

    # do the comparison
    a = get_json(args[1])
    b = get_json(args[2])

    if lenient_end:
      pops=0
      while len(b) > len(a) > 0:
        b.pop()
        pops += 1
      while len(a) > len(b) > 0:
        a.pop()
        pops += 1
      print "Trimmed off " + str(pops) + " lines!"

    d = compare_json_data(a, b, c)

    if print_max_rel_diff:
        sys.stderr.write(str(c.max_floating_point_relative_difference()) + '\n')

    # print results if verbose
    if d[0] and verbose:
        print json.JSONEncoder().encode(d[1])

    if diff_tool != None:
        from JsonStruct import JsonStruct

        left = []
        right = []

        al = len(a)
        bl = len(b)

        # loop over the longer of the two arrays
        for i in range(0, max(al, bl)):
            a_data = {} if i >= al else a[i]
            b_data = {} if i >= bl else b[i]

            left += [a_data]
            index = 'line ' + str(i+1)
            if index in d[1]:
                from copy import deepcopy
                d_data = deepcopy(a_data)
                d_data = apply_differences(d_data, d[1][index])
                right += [d_data]
            else:
                right += [a_data]

        m = '-----------'
        import time
        t = str(int(time.time()))
        left_file_name = args[1] + ".jdiff." + t
        left_file  = open(left_file_name,  'w')
        n = 0
        for a in left:
            left_file.write(m + ' Start Line #' + m + '\n' \
                                + str(JsonStruct(a)) + m + \
                                ' End Line #' + m + '\n')
            n += 1
        right_file_name = args[2] + ".jdiff." + t
        right_file = open(right_file_name, 'w')
        n = 0
        for b in right:
            right_file.write(m + ' Start Line #' + m + '\n' \
                                 + str(JsonStruct(b)) + m + \
                                 ' End Line #' + m + '\n')
            n += 1
        left_file.close()
        right_file.close()

        args = diff_tool.split(" ") + [left_file_name, right_file_name];
        import subprocess
        subprocess.call(args)

    # exit code is number of differing lines
    sys.exit(d[0])
