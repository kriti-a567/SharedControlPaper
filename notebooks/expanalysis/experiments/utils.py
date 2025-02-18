"""
expanalysis/experiments/utils.py: part of expfactory package
functions for working with experiment factory Result.data dataframe
"""

import pandas
import unicodedata
import re

def get_data(row):
    """Data can be stored in different forms depending on the experiment template.
    This function returns the data in a standard form (a list of trials)
    :row:  one row of a results dataframe
    """
    def get_response_text(question):
        """Returns the response text that corresponds to the value recorded in a survey question
        :question: A dictionary corresponding to a survey question
        """
        val = question['response']
        if 'options' in question.keys():
            options = question['options']
            text = [lookup_val(opt['text']) for opt in options if 'value' in opt.keys() and opt['value'] == val]
            if len(text) == 1: text = text[0]
        else:
            text = pandas.np.nan
        return text
    try:
        data = row['data']
    except:
        print('No data column found!')
    if row['experiment_template'] == 'jspsych':
        if len(data) == 1:
            return data[0]['trialdata']
        elif len(data) > 1:
           return  [trial['trialdata'] for trial in data]
        else:
            print("No data found")
    elif row['experiment_template'] == 'survey':
        survey =  data.values()
        for i in survey:
            i['question_num'] = int(re.search(r'%s_([0-9]{1,2})*' % row['experiment_exp_id'], i['id']).group(1))
            i['response_text'] = get_response_text(i)
            i['text'] = lookup_val(i['text'])
        survey = sorted(survey, key=lambda k: k['question_num'])
        return survey
    elif row['experiment_template'] == 'unknown':
        print("Couldn't determine data template")

        
def drop_null_cols(df):
    null_cols = df.columns[pandas.isnull(df).sum()==len(df)]     
    df.drop(null_cols,axis = 1, inplace = True)
    
def lookup_val(val):
    """function that modifies a string so that it conforms to expfactory analysis by 
    replacing it with an interpretable synonym
    :val: val to lookup
    """
    try:
        is_str = isinstance(val,(str,unicode))
    except NameError:
        is_str = isinstance(val,str)
    
    if is_str:
        #convert unicode to str
        try:
            if isinstance(val, unicode):
                val = unicodedata.normalize('NFKD', val).encode('ascii', 'ignore')
        except NameError:
            pass
        lookup_val = val.strip().lower()
        lookup_val = val.replace(" ", "_")
        #define synonyms
        lookup = {
        'reaction time': 'rt',
        'instructions': 'instruction',
        'correct': 1,
        'incorrect': 0}
        return lookup.get(lookup_val,val)
    else:
        return val
        
def remove_duplicates(data):
    # Three should only be one value per worker/finishtime combo
    counts = data.groupby(['worker_id', 'finishtime']).count().experiment_exp_id.reset_index()
    duplicates = counts[counts.experiment_exp_id>1]
    for i,d in duplicates.iterrows():
        worker, finishtime = d[['worker_id','finishtime']]
        data.drop(data[(data.worker_id == worker) & (data.finishtime == finishtime)].index[1:], inplace = True)
    
def result_filter(data, battery = None, exp_id = None, worker = None, template = None, finishtime = None):
    '''Subset results data to the specific battery(s), experiment(s) or worker(s). Each
        attribute may be an array or a string. If reset is true, the data will
        be reset to a cleaned dataframe
    :data: the data from an expanalysis Result object
    :param battery: a string or array of strings to select the battery(s)
    :param experiment: a string or array of strings to select the experiment(s)
    :param worker: a string or array of strings to select the worker(s)
    :param template: a string or array of strings to select the expfactory templates
    :param finishtime: either a string indicating the time when all data should come after, or a tuple
    with the string, followed by a boolean indicating what select_finishtime should set all_data to
    '''

    if template != None:
        data = select_template(data, template)
    if worker != None:
        data = select_worker(data, worker)
    if battery != None:
        data = select_battery(data, battery)
    if exp_id != None:
        data = select_experiment(data, exp_id)
    if finishtime != None:
        if isinstance(finishtime, str):
            data = select_finishtime(data,finishtime)
        else:
            data = select_finishtime(data, finishtime[0], finishtime[1])
    return data

    
def select_battery(data, battery):
    '''Selects a battery (or batteries) from results object and sorts based on worker and time of experiment completion
    :data: the data from an expanalysis Result object
    :battery: a string or array of strings to select the battery(s)
    :return df: dataframe containing the appropriate result subset
    '''
    assert 'battery_name' in data.columns, \
        'battery_name field must be in the dataframe'
    Pass = True
    if not isinstance(battery, list):
        battery = [battery] 
    for b in battery:
        if not b in data['battery_name'].values:
            print("Alert!:  The battery '%s' not found in results. Try resetting the results" % (b))
            Pass = False
    assert Pass == True, "At least one battery was not found in results"
    df = data.query("battery_name in %s" % battery)
    df = df.sort_values(by = ['battery_name', 'experiment_exp_id', 'worker_id', 'finishtime'])
    df.reset_index(inplace = True, drop = True)
    return df
    
def select_experiment(data, exp_id):
    '''Selects an experiment (or experiments) from results object and sorts based on worker and time of experiment completion
    :data: the data from an expanalysis Result object
    :param exp_id: a string or array of strings to select the experiment(s)
    :return df: dataframe containing the appropriate result subset
    '''
    assert 'experiment_exp_id' in data.columns, \
        'experiment_exp_id field must be in the dataframe'
    Pass = True
    if not isinstance(exp_id, list):
        exp_id = [exp_id]
    for e in exp_id:
        if not e in data['experiment_exp_id'].values:
            print("Alert!: The experiment '%s' not found in results. Try resetting the results" % (e))
            Pass = False
    assert Pass == True, "At least one experiment was not found in results"
    df = data.query("experiment_exp_id in %s" % exp_id)
    df = df.sort_values(by = ['experiment_exp_id', 'worker_id', 'battery_name', 'finishtime'])
    df.reset_index(inplace = True, drop = True)
    return df
    
def select_worker(data, worker):
    '''Selects a worker (or workers) from results object and sorts based on experiment and time of experiment completion
    :data: the data from an expanalysis Result object
    :worker: a string or array of strings to select the worker(s)
    :return df: dataframe containing the appropriate result subset
    '''
    assert 'worker_id' in data.columns, \
        'worker_id field must be in the dataframe'
    Pass = True
    if not isinstance(worker, list):
            worker = [worker]
    for w in worker:
        if not w in data['worker_id'].values:
            print("Alert!: The experiment '%s' not found in results. Try resetting the results" % (w))
            Pass = False
    assert Pass == True, "At least one worker was not found in results"
    df = data.query("worker_id in %s" % worker)
    df = df.sort_values(by = ['worker_id', 'experiment_exp_id', 'battery_name', 'finishtime'])
    df.reset_index(inplace = True, drop = True)
    return df   

def select_template(data, template):
    '''Selects a template (or templates) from results object and sorts based on experiment and time of experiment completion
    :data: the data from an expanalysis Result object
    :template: a string or array of strings to select the worker(s)
    :return df: dataframe containing the appropriate result subset
    '''
    assert 'experiment_template' in data.columns, \
        'experiment_template field must be in the dataframe'
    if not isinstance(template, list):
        template = [template]
    template = map(str.lower,template)
    df = data.query("experiment_template in %s" % template)
    assert len(df) != 0, "At least one template was not found in results"
    df = df.sort_values(by = ['worker_id', 'experiment_exp_id', 'battery_name', 'finishtime'])
    df.reset_index(inplace = True, drop = True)
    return df
    
def select_finishtime(data, finishtime, all_data = True):
     '''Get results after a finishtime 
    :data: the data from an expanalysis Result object
    :finishtime: a date string
    :param all_data: boolean, default True. If true, only select data where the entire dataset was collected afte rthe finishtime
    :return df: dataframe containing the appropriate result subset
    '''
     assert 'finishtime' in data.columns, \
        'finishtime field must be in the dataframe'
     if all_data and 'worker_id' in data.columns:
        passed_df = data.groupby('worker_id')['finishtime'].min() >= finishtime
        workers = list(passed_df[passed_df].index)
        df = select_worker(data, workers)
     else:
        df = data.query('finishtime >= "%s"' % finishtime) 
        df.reset_index(inplace = True, drop = True)
     return df
    
