import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(localStorage.getItem('authToken'));
    const [user, setUser] = useState(null); // NEW: State to hold user profile data

    // This effect runs when the app loads to fetch the user profile if a token exists
    useEffect(() => {
        const fetchUserProfile = async () => {
            if (token) {
                try {
                    const response = await axios.get('http://127.0.0.1:5000/api/profile', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    setUser(response.data);
                } catch (error) {
                    console.error("Failed to fetch user on initial load, logging out.", error);
                    logout(); // The token is invalid, so log out
                }
            }
        };
        fetchUserProfile();
    }, [token]); // It runs whenever the token changes

    const login = async (newToken) => {
        localStorage.setItem('authToken', newToken);
        setToken(newToken);
        // After setting the token, user will be fetched by the useEffect hook.
    };

    const logout = () => {
        localStorage.removeItem('authToken');
        setToken(null);
        setUser(null); // Clear user data on logout
    };

    const isAuthenticated = !!token;

    return (
        <AuthContext.Provider value={{ isAuthenticated, token, user, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    return useContext(AuthContext);
};