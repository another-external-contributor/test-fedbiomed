import React, {useState} from 'react';
import {
    EuiButton,
    EuiFieldPassword,
    EuiTitle,
    EuiFlexGroup,
    EuiFlexItem,
    EuiForm,
    EuiFormRow,
    EuiSpacer,
    EuiToast,
    EuiToolTip,
} from "@elastic/eui";
import {EP_UPDATE_PASSWORD} from "../../constants";
import axios from "axios";

const initialPassForm = {old_password: '', password: '', confirm_password: ''}
const initialNotif = {show : false, message : '', title: ''}
const PasswordChange = (props) => {

    const [passForm, setPassForm] = useState(initialPassForm)
    const [notif, setNotif] = useState(initialNotif)
    const notClose = () => setNotif(initialNotif)
    const handleChange = (e) => setPassForm({...passForm, [e.target.name] : e.target.value})
    const resetForm = () => setPassForm(initialPassForm)

    /**
     * On password form is submitted
     * @param e
     */
    const onSubmitNewPassword = (e) => {
        e.preventDefault()

        // check if both password matches, otherwise displays error message
        if (passForm.password === passForm.confirm){
            sendPassword(passForm.password , EP_UPDATE_PASSWORD)
        } else {
            setNotif({show:true,  title: "Error", message: 'Please make sure passwords are same.'})
        }
    }

    /**
     * API call for updating password
     * @param new_password
     * @param url
     */
    const sendPassword = (new_password, url) => {
        let data = {email: props.user.email, password: new_password}
        axios.post(url, data)
             .then((response) => {
                 setNotif({show:true,  title: "Success", message: 'Password has been successfully changed.'})
                 resetForm()
                 setTimeout(() => [
                     setNotif(initialNotif)
                 ], 7000)
             })
             .catch((error) => {
                if (error.response) {
                    setNotif({show:true,  title: "Error", message: error.response.data.message })
                }else{
                    setNotif({show:true,  title: "Error", message: 'Incorrect password' + error.toString() })
                }
            })
    }


    return (
        <React.Fragment>
            <EuiTitle>
                <h2>Change/Update Password</h2>
            </EuiTitle>
            <EuiForm component="form"  onSubmit={onSubmitNewPassword} >
                 <EuiFlexGroup direction="column" >
                     <EuiFlexItem grow={false}>
                         {notif.show ? (
                             <React.Fragment>
                                 <EuiSpacer size="l" />
                                 <EuiToast
                                        title={notif.title}
                                        color={notif.title === "Error" ? "danger" : "success"}
                                        iconType="alert"
                                        onClose={notClose}
                                        style={{width:400}}
                                      >
                                     <p>{notif.message}</p>
                                 </EuiToast>
                             </React.Fragment>

                         ) : null}
                     </EuiFlexItem>
                     <EuiFlexItem grow={false}>
                          <EuiFormRow label={"Old Password"} hasEmptyLabelSpace>
                             <EuiFieldPassword
                                    type='dual'
                                    name={"old_password"}
                                    value={passForm.old_password}
                                    onChange={handleChange}
                              />
                         </EuiFormRow>
                     </EuiFlexItem>
                     <EuiFlexItem grow={false}>
                          <EuiFormRow label={"Password"} hasEmptyLabelSpace>
                            <EuiToolTip
                                  display={"block"}
                                  position="right"
                                  title={"Attention!"}
                                  content="Password should be at least 8 character long,
                                  with at least one special char, one upper case  and number"
                            >
                                 <EuiFieldPassword
                                        type='dual'
                                        name={"password"}
                                        value={passForm.password}
                                        onChange={handleChange}
                                  />
                            </EuiToolTip>
                         </EuiFormRow>
                     </EuiFlexItem>
                     <EuiFlexItem grow={false}>
                          <EuiFormRow label={"Confirm Password"} hasEmptyLabelSpace>
                            <EuiToolTip
                                  display={"block"}
                                  position="right"
                                  title={"Attention!"}
                                  content="Password should be at least 8 character long,
                                  with at least one special char, one upper case  and number"
                            >
                                 <EuiFieldPassword
                                        type='dual'
                                        name={"confirm"}
                                        value={passForm.confirm}
                                        onChange={handleChange}
                                  />
                            </EuiToolTip>
                         </EuiFormRow>
                     </EuiFlexItem>
                     <EuiFlexItem grow={false} >
                         <EuiFormRow display="center">
                            <EuiButton type="submit" fill>
                                Update Password
                            </EuiButton>
                         </EuiFormRow>
                     </EuiFlexItem>
                 </EuiFlexGroup>
            </EuiForm>
        </React.Fragment>
    );
};

export default PasswordChange;
