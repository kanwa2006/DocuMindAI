import axios from "axios";
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const api = axios.create({ baseURL: BASE_URL, headers: { "Content-Type": "application/json" } });
api.interceptors.request.use(config => { const t=localStorage.getItem("token"); if(t) config.headers.Authorization=`Bearer ${t}`; return config; });
api.interceptors.response.use(r=>r, error => {
  if(error.response?.status===401){localStorage.removeItem("token");localStorage.removeItem("username");window.location.href="/login";}
  return Promise.reject(error);
});

export const authAPI = {
  login:(username,password)=>{const f=new FormData();f.append("username",username);f.append("password",password);return api.post("/auth/login",f,{headers:{"Content-Type":"application/x-www-form-urlencoded"}});},
  register:(data)=>api.post("/auth/register",data),
  me:()=>api.get("/auth/me"),
  changePassword:(data)=>api.post("/auth/change-password",data),
  forgotPassword:(data)=>api.post("/auth/forgot-password",data),
  sendOTP:(data)=>api.post("/auth/send-otp",data),
  checkOTP:(data)=>api.post("/auth/check-otp",data),
  verifyOTP:(data)=>api.post("/auth/verify-otp",data),
};

export const docsAPI = {
  upload:(file)=>{const f=new FormData();f.append("file",file);return api.post("/documents/upload",f,{headers:{"Content-Type":"multipart/form-data"}});},
  list:()=>api.get("/documents/list"),
  delete:(id)=>api.delete(`/documents/${id}`),
  info:(id)=>api.get(`/documents/info/${id}`),
  getViewUrl:(id)=>{const t=localStorage.getItem("token");return `${BASE_URL}/documents/view/${id}?token=${t}`;},
};

export const qaAPI = {
  ask:(question)=>api.post("/qa/ask",{question}),
  history:()=>api.get("/qa/history"),
  clearHistory:()=>api.delete("/qa/history"),
};

export default api;
