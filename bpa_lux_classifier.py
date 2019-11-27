import os
import sys
import numpy as np
import time
import subprocess
import tensorflow as tf
import matplotlib.pyplot as plt
import aLib
from aLib import dp
from preprocess import get_data


###################################

class Model(tf.keras.Model):
    def __init__(self):
        """
        Model architecture for pulse classification. Contains forward pass, accuracy, and loss.
		"""
        super(Model, self).__init__()
        
        # Model Hyperparameters
        self.batch_size = 50
        self.num_classes = 4
        self.learning_rate = 2e-3
        self.drop_rate = 0.1

        # Model Layers
        self.dense1 = tf.keras.layers.Dense(self.num_classes*4, activation = 'relu', dtype=tf.float32, name='dense1')
        self.dense2 = tf.keras.layers.Dense(self.num_classes*3, activation = 'relu', dtype=tf.float32, name='dense2')
        self.dense3 = tf.keras.layers.Dense(self.num_classes*2, activation = 'relu', dtype=tf.float32, name='dense3')
        self.dense4 = tf.keras.layers.Dense(self.num_classes, dtype=tf.float32, name='dense4')

        # Initialize Optimizer
        self.optimizer = tf.keras.optimizers.Adam(learning_rate = self.learning_rate)
        
        

    def call(self, inputs):
        """
        Performs the forward pass on a batch of RQs to generate pulse classification probabilities. 

        :param inputs: a batch of RQ pulses of size [batch_size x num_RQs] 
        :return: A [batch_size x num_classes] tensor representing the probability distribution of pulse classifications
        """
        
        # Forward pass on inputs
        dense1_output = self.dense1(inputs)
        dense2_output = self.dense2(dense1_output)
        dense3_output = self.dense3(dense2_output)
        dense4_output = self.dense4(dense3_output)
        
        
        # Probabilities of each classification
        probabilities = tf.nn.softmax(dense4_output)

        return(probabilities)


    def loss_function(self, probabilities, labels):
        """
        Calculate model's cross-entropy loss after one forward pass.
        
		:param probabilities: tensor containing probabilities of RQ classification prediction     [batch_size x num_classes]
		:param labels: tensor containing RQ classification labels                                 [batch_size x num_classes]

        :return: model loss as a tensor
        """
        return(tf.reduce_mean(tf.keras.losses.sparse_categorical_crossentropy(labels, probabilities)))


    def accuracy_function(self, probabilities, labels):
        """
		Calculate model's accuracy by comparing logits and labels.
        
		:param probabilities: tensor containing probabilities of RQ classification prediction     [batch_size x num_classes]
		:param labels: tensor containing RQ classification labels                                 [batch_size x num_classes]
        
		:return: model accuracy as scalar tensor
		"""
        correct_predictions = tf.equal(tf.argmax(probabilities, 1), labels)
        return(tf.reduce_mean(tf.cast(correct_predictions, dtype = tf.float32)))



def train(model, inputs, labels):
    """
    This function should train your model for one episode.
    Each call to this function should generate a complete trajectory for one episode (lists of states, action_probs,
    and rewards seen/taken in the episode), and then train on that data to minimize your model loss.
    Make sure to return the total reward for the episode.

    :param model: The model
    :param data: LUX RQ data, preprocessed
    :return: The total reward for the episode
    """
    t = time.time()
    print_counter = 0
    
    accuracy = 0
    batch_counter = 0

    # Loop through inputs in model.batch_size increments
    for start, end in zip(range(0, inputs.shape[0] - model.batch_size, model.batch_size),
                          range(model.batch_size, inputs.shape[0], model.batch_size)):
        batch_counter += 1

        # Redefine batched inputs and labels
        batch_inputs = inputs[start:end]
        batch_labels = labels[start:end]
        
        with tf.GradientTape() as tape:
            probabilities = model(batch_inputs)           # probability distribution for pulse classification
            loss = model.loss_function(probabilities, batch_labels)     # loss of model

        accuracy += model.accuracy_function(probabilities, batch_labels)
        # Update
        gradients = tape.gradient(loss, model.trainable_variables)
        model.optimizer.apply_gradients(zip(gradients, model.trainable_variables))
        
#        # Print Current Progress
#        if start/inputs.shape[0] >= print_counter:
#            print_counter += 0.2                                                # Update print counter
#            accuracy_mean = accuracy/batch_counter                              # Get current model accuracy
#            print("{0:.0%} complete, Time = {1:2.1f} min, Accuracy = {2:.0%}".format(end/inputs.shape[0], (time.time()-t)/60, accuracy_mean))

    return None

def test(model, inputs, labels):
    
    batch_counter = 0
    accuracy = 0
    loss = 0
    
    for start, end in zip(range(0, inputs.shape[0] - model.batch_size, model.batch_size), 
                          range(model.batch_size, inputs.shape[0], model.batch_size)):    
        batch_counter += 1
        
        batch_inputs = inputs[start:end]
        batch_labels = labels[start:end]
        
        probabilities = model(batch_inputs)
        loss += model.loss_function(probabilities, batch_labels)
        accuracy += model.accuracy_function(probabilities, batch_labels)
        
    loss /= batch_counter
    accuracy /= batch_counter
    
    return accuracy#, loss


def main():

#%%    
    # dataset_list = ["lux10_20160627T0824_cp24454"] # Short pulse DD data
    #dataset_list = ['lux10_20160802T1425']  # Small piece of Kr + DD data
    dataset_list = ['lux10_20130425T1047'] # Run03 Kr83 dataset. Target ~10 Hz of Krypton.

    # Generic pulse finding RQs
    # fields = ["pulse_area_phe", "luxstamp_samples", "pulse_classification",
    #           "s1s2_pairing", "z_drift_samples", "cor_x_cm", "cor_y_cm",
    #           "top_bottom_ratio", "rms_width_samples", "xyz_corrected_pulse_area_all_phe",
    #           "event_timestamp_samples", 'file_number']

    # Decide which RQs to use. 1 for original LPC (1-to-1 comparison) vs 2 for larger list of RQs.
    RQ_list_switch = 1
    if RQ_list_switch == 1:
        #Below: RQs used by the standard LUX Pulse Classifier
        fields = ['pulse_area_phe',  # OG LPC
                    'luxstamp_samples',  # OG LPC
                    's2filter_max_area_diff',  # OG LPC
                    'prompt_fraction_tlx',  # OG LPC
                    'top_bottom_asymmetry',  # OG LPC
                    'aft_t0_samples',  # OG LPC
                    'aft_t1_samples',  # OG LPC
                    'aft_t2_samples',  # OG LPC
                    'peak_height_phe_per_sample',  # OG LPC
                    'skinny_peak_area_phe',  # OG LPC
                    'prompt_fraction',  # OG LPC
                    'pulse_height_phe_per_sample',  # OG LPC
                    'file_number',  # OG LPC
                    'pulse_classification']
    elif RQ_list_switch == 2:
        # RQs used by the standard LUX Pulse Classifier + Additional ones for better performance
        # Currently up-to-date with google sheets list as of 112719T1206
        fields = ['pulse_area_phe',  # OG LPC
                  'luxstamp_samples',  # OG LPC
                  's2filter_max_area_diff',  # OG LPC
                  'prompt_fraction_tlx',  # OG LPC
                  'top_bottom_asymmetry',  # OG LPC
                  'aft_t0_samples',  # OG LPC
                  'aft_t05_samples',
                  'aft_t25_samples',
                  'aft_t1_samples',  # OG LPC
                  'aft_t75_samples',
                  'aft_t95_samples',
                  'aft_t2_samples',  # OG LPC
                  'peak_height_phe_per_sample',  # OG LPC
                  'skinny_peak_area_phe',  # OG LPC
                  'prompt_fraction',  # OG LPC
                  'pulse_height_phe_per_sample',  # OG LPC
                  'cor_x_cm',
                  'cor_y_cm',
                  'file_number',  # OG LPC
                  #'s1s2pairing', # may help later for finding Kr events?
                  'pulse_classification',
                  #  ADD MORE RQs HERE  #
                  ]
                  

#    rq = get_data(dataset_list, fields)
#    print('All RQs loaded!')
#
#    # Create some variables for ease of broad event classification and population checking.
#    pulse_classification = rq[0].pulse_classification
#    num_pulses = np.sum(pulse_classification > 0, axis=0)
#    num_S1s = np.sum(pulse_classification == 1,axis=0)
#    num_S2s = np.sum(pulse_classification == 2,axis=0)
#    num_se = np.sum(pulse_classification == 3, axis=0)
#    num_sphe = np.sum(pulse_classification == 4, axis=0)
    print('[end file]')
#    rqs, labels, pulse_event_index  = get_data(dataset_list, fields)
    print('All RQs loaded!')

    # Create some variables for ease of broad event classification and population checking.
#    pulse_classification = labels
#    num_pulses = np.sum(pulse_classification > 0, axis=0)
#    num_S1s = np.sum(pulse_classification == 1,axis=0)
#    num_S2s = np.sum(pulse_classification == 2,axis=0)
#    num_se = np.sum(pulse_classification == 3, axis=0)
#    num_sphe = np.sum(pulse_classification == 4, axis=0)



    # Pull data using preprocessing
    train_rqs, train_labels, pulse_event_index, test_rqs, test_labels, test_event_index = get_data(dataset_list, fields)
    train_labels = train_labels - 1
    test_labels = test_labels - 1

#%%
#    print('pulse rq shape', pulse_rqs.shape)
#    print('labels shape', labels.shape)
#    print('pulse event index shape', pulse_event_index.shape)
    
#    print('labels',labels[:,0])   
#    print(pulse_event_index[0:11])
    # print((train_rqs[80:81]))
    # print((test_rqs == - 999999).sum())
    
#%%
    # Define model
    model = Model()


    t = time.time()
    # Train model
    epochs = 10
    for epoch in range(epochs):
        train(model, train_rqs, train_labels)
        test_acc = test(model, test_rqs, test_labels)
        print("Epoch {0:1d} Complete.\nTotal Time = {1:2.1f} minutes, Testing Accuracy = {2:.0%}".format(epoch+1, (time.time()-t)/60, test_acc))



if __name__ == '__main__':
    main()

