# Add this to a utils.py file
_tensorflow = None

def get_tensorflow():
    global _tensorflow
    if _tensorflow is None:
        # Suppress warnings during import
        import os
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
        
        import tensorflow as tf
        # Set logging level
        tf.get_logger().setLevel('ERROR')
        _tensorflow = tf
    return _tensorflow