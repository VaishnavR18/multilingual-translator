import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { signInWithGoogle, auth } from "../firebaseconfig";
import { FiLogIn, FiLogOut, FiUser } from "react-icons/fi";

import "./Navbar.css";

const Navbar = () => {
  const [userEmail, setUserEmail] = useState(null);

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      if (user) {
        setUserEmail(user.email);
        localStorage.setItem("userEmail", user.email);
      } else {
        setUserEmail(null);
        localStorage.removeItem("userEmail");
      }
    });

    return () => unsubscribe();
  }, []);

  const handleLogin = async () => {
    await signInWithGoogle();
  };

  const handleLogout = async () => {
    await auth.signOut();
    localStorage.removeItem("userEmail");
    setUserEmail(null);
  };

  return (
    <nav className="navbar">
      <div className="navbar-logo">
        <Link to="/" aria-label="Home">
          Translator<span className="logo-highlight">App</span>
        </Link>
      </div>

      <div className="navbar-links">
        <Link to="/" className="nav-link">Home</Link>
        <Link to="/translate" className="nav-link">Translate</Link>
      </div>

      <div className="navbar-auth">
        {!userEmail ? (
          <button onClick={handleLogin} className="btn login-btn" aria-label="Login">
            <FiLogIn className="icon" /> Login
          </button>
        ) : (
          <div className="user-info">
            <FiUser className="icon user-icon" />
            <span className="user-email" title={userEmail}>
              {userEmail.length > 18 ? userEmail.slice(0, 18) + "..." : userEmail}
            </span>
            <button onClick={handleLogout} className="btn logout-btn" aria-label="Logout">
              <FiLogOut className="icon" /> Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
