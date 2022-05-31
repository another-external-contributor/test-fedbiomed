
// API Endpoints
export const EP_DATASET_PREVIEW = '/api/datasets/preview'
export const EP_DATASETS_LIST   = '/api/datasets/list'
export const EP_DATASET_REMOVE   = '/api/datasets/remove'
export const EP_REPOSITORY_LIST = '/api/repository/list'
export const EP_DATASET_UPDATE  = '/api/datasets/update'
export const EP_DATASET_ADD     = '/api/datasets/add'
export const    EP_DEFAULT_DATASET_ADD     = '/api/datasets/add-default-dataset'
export const EP_CONFIG_NODE_ENVIRON = '/api/config/node-environ'
export const EP_LOAD_CSV_DATA = '/api/datasets/get-csv-data'

// BIDS Dataset Endpoints
export const EP_VALIDATE_BIDS_ROOT = '/api/datasets/bids/validate-bids-root'
export const EP_VALIDATE_REFERENCE_COLUMN = '/api/datasets/bids/validate-reference-column'
export const EP_ADD_BIDS_DATASET = '/api/datasets/bids/add'
export const EP_PREVIEW_BIDS_DATASET = '/api/datasets/bids/preview'

// Messages
export const DATA_NOTFOUND = 'There is no data found for the dataset. It might be deleted'

// Form Handler
export const ADD_DATASET_ERROR_MESSAGES = {
    0 : { key: 'name', message: 'Dataset name is a required field'},
    1 : { key: 'type', message: 'Please select data type'},
    2 : { key: 'path', message: 'Please select data file'},
    3 : { key: 'tags', message: 'Please enter at least one tag for the dataset'},
    4 : { key: 'desc', message: 'Please enter a description for dataset'}
}

//Allowed file extensions for data loader
export const ALLOWED_EXTENSIONS = ['.csv', '.txt']

