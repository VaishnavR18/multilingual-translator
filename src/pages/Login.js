import React, { useState, useEffect } from "react";
import { signInWithGoogle, auth } from "../firebaseconfig";
import { useNavigate } from "react-router-dom";

const Login = () => {
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((currentUser) => {
      if (currentUser) {
        setUser(currentUser.email);
        localStorage.setItem("userEmail", currentUser.email);
        navigate("/translate");
      }
    });
    return () => unsubscribe(); // Cleanup
  }, [navigate]);

  const handleLogin = async () => {
    await signInWithGoogle();
  };

  return (
    <div>
      <h2>Login</h2>
      <button onClick={handleLogin}>Sign in with Google</button>
    </div>
  );
};

export default Login;
