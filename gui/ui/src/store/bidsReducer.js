/**
 * Initial state for BIDS data format
 * @type {{identifiers: {}, format: null, folder_path: null}}
 */
const initialState = {
    bids_root: null,
    patient_folders: null,
    modalities : null,
    bids_ref : {
        ref : {index: null, name:null},
        subjects: {
            available_subject : null,
            missing_entries: null,
            missing_folders: null
        }
    },
    metadata : {
        name: null,
        tags: null,
        desc: null,
    },
    reference_csv: null,
    ignore_reference_csv: false,
}


/**
 * BIDS format dataset creation global state management
 * @param state
 * @param action
 * @returns {{identifiers, format: null, folder_path: null}|{identifiers: {}, format: null,
 *            folder_path: null}|{identifiers: {}, format: null, folder_path}}
 */
export const bidsReducer = (state = initialState, action) => {

    switch (action.type){
        case "SET_BIDS_ROOT":
            return {...state, bids_root: action.payload.root_path, modalities: action.payload.modalities}

        case "RESET_BIDS_ROOT":
            return {...state, bids_root: null, modalities: null }

        case "SET_FORMAT":
            return { ...state, patient_folders: action.payload}

        case "SET_REFERENCE_CSV":
            return {...state, reference_csv : action.payload}

        case "SET_BIDS_METADATA":
            return {...state, metadata: { ...state.metadata, ...action.payload} }

        case "SET_IDENTIFIERS":
            return {...state, identifiers: action.payload}

        case "SET_BIDS_REF":
            return {...state, bids_ref: {ref : action.payload.ref,
                                         subjects: {available_subjects : action.payload.subjects.available_subjects,
                                                    missing_entries: action.payload.subjects.missing_entries,
                                                    missing_folders: action.payload.subjects.missing_folders}
                                        }}

        case "RESET_BIDS_REF":
            return {...state,bids_ref : initialState.bids_ref}

        case "RESET_BIDS_REFERENCE_CSV":
            return {...state, bids_ref : initialState.bids_ref, reference_csv : null}

        case "SET_IGNORE_REFERENCE_CSV":
            return {...state, ignore_reference_csv : action.payload }

        case "RESET_BIDS":
            return initialState

        default:
            return state
    }
}

const bidsPreviewInitialstate = {
    subject_table : null,
    modalities : null,
    dataset_id : null,
}

/**
 * State reducer for BIDS preview
 * @param state
 * @param action
 * @returns {{modalities: null, dataset_id: null, subject_table: null}|*}
 */
export const bidsPreviewReducer = (state = bidsPreviewInitialstate, action) => {

    switch (action.type){
        case "SET_BIDS_PREVIEW":
            return action.payload
        default:
            return state
    }
}

