import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import { AuthProvider, RequireAdmin, RequireAuth } from "./auth";
import { Layout } from "./layout";
import { Login } from "./pages/Login";
import { Accept } from "./pages/Accept";
import { Chat } from "./pages/Chat";
import { Tools } from "./pages/Tools";
import { Keys } from "./pages/Keys";
import { Members } from "./pages/Members";
import { Permissions } from "./pages/Permissions";
import { Audit } from "./pages/Audit";
import { Servers } from "./pages/Servers";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 5000 } } });
ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><QueryClientProvider client={queryClient}><BrowserRouter><AuthProvider><Routes><Route path="/login" element={<Login />} /><Route path="/accept" element={<Accept />} /><Route element={<RequireAuth />}><Route element={<Layout />}><Route index element={<Navigate to="/tools" replace />} /><Route path="/tools" element={<Tools />} /><Route path="/keys" element={<Keys />} /><Route path="/chat" element={<Chat />} /><Route element={<RequireAdmin />}><Route path="/servers" element={<Servers />} /><Route path="/members" element={<Members />} /><Route path="/permissions" element={<Permissions />} /><Route path="/audit" element={<Audit />} /></Route></Route></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes></AuthProvider></BrowserRouter></QueryClientProvider></React.StrictMode>);
