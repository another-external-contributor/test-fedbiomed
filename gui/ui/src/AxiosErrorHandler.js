
import axios from 'axios';
import {EP_REFRESH} from './constants';
import { getAccessToken, checkIsTokenActive, getRefreshToken }  from './store/actions/authActions';
import { createBrowserHistory } from 'history';

// this handler wraps axios logic request:
// it does mainly 2 things:
// 1. formats request with correct header (for token auth)
// 2. contains logic for getting refresh tokens, and ensuring idle user are disconnected

const handleTokenExpiration = (msg=null) =>
  {
    // logic for handling token expiration after a 401 HTTP error request (unauthorized)
    if (msg === null){
      alert("Error 401: session expired, please login again")
    }else{
      alert(msg)
    }
    
    window.location.href = '/login/';  // redirect to login page 
  }


  // Add a request interceptor
  axios.interceptors.request.use(function (req) {

      const token = getAccessToken();
      if (token && req.url !== EP_REFRESH){
        // set headers as required by jst_extended library (flask server side)
        req.headers.Authorization = `Bearer ${token}`;
      }
      return req;
    }, function (error) {
      // Do something with request error
      return Promise.reject(error);
    });


    
  // Add a response interceptor
  axios.interceptors.response.use(function (response) {
      // Any status code that lie within the range of 2xx cause this function to trigger
      // Do something with response data

      return response;
    }, function (error) {
      // Any status codes that falls outside the range of 2xx cause this function to trigger
      // Do something with response error
      const history = new createBrowserHistory();

      //return new Promise((resolve, reject) => {
        return new Promise((resolve, reject) => {
        switch (error.request.status){
          case 404:
            // should be handled by React's Router (see App.js)
            reject(error)
            console.log("HTTP ERROR 404");
            break;
  
          case 401:
            // we should differentiate case where token has expired with case "insufficient privileged"
            let access_token = getAccessToken();
            let is_token_expired = checkIsTokenActive();
  
            // let s retrieve token (if any)
            if (access_token){
  
              if (is_token_expired){
                let refresh_token = getRefreshToken();
                if (error.response.config.url !== EP_REFRESH){
                  const originalRequest = error.config;
                  axios.get(EP_REFRESH,
                   {headers: 
                    {
                      'Authorization':  `Bearer ${refresh_token}`
                    }
                  })
                  .then(res => {

                    let new_access_token = res.data.result.access_token;
                    let new_refresh_token = res.data.result.refresh_token;
                    sessionStorage.setItem('accessToken', new_access_token);
                    sessionStorage.setItem('refreshToken', new_refresh_token);

                    resolve(axios(originalRequest))
                  })
                  .catch(rf_error => {
                    // at this point, refresh token should have expired (as well as access token)
                    reject(rf_error);
                    alert(error.response.data.message)
                  })
                } else {
                  // case where refresh token has expired
                  handleTokenExpiration(error.response.data.message)
                }
                
                
                
              }
              else{
                alert("Unsufficient privileges")
                //redirect to previous page
                history.back()
              }
            }else{
              let link = window.location.href.toString().split(window.location.host)[1];
              if ( (link !== '/login') && ( link !== '/login/')){
                handleTokenExpiration(error.response.data.message)
              } else{
                reject(error)
              }
  
            }
            break;
          default:
            reject(error)
            break;
        }
      })
    });


export default axios;

  