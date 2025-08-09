import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import {getFirestore} from "firebase/firestore";


const firebaseConfig = {
  apiKey: "AIzaSyCx8Kepco4rNw6GCwJ9qwj5mZMZZPzYb7M",
  authDomain: "translator-54b1c.firebaseapp.com",
  projectId: "translator-54b1c",
  storageBucket: "translator-54b1c.firebasestorage.app",
  messagingSenderId: "249101219464",
  appId: "1:249101219464:web:4d80a2652ebaaad8c2113d",
  measurementId: "G-6QSL74VC6T"
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app); // Auth instance
const provider = new GoogleAuthProvider(); // Google auth provider
export const db=getFirestore(app);
 // Firebase analytics (optional, can be removed if not needed)


// Export Google sign-in function
export const signInWithGoogle = async () => {
  try {
    const result = await signInWithPopup(auth, provider); // Popup for Google sign-in
    return result.user.email; // Return the email address of the signed-in user
  } catch (error) {
    console.error("Error during Google sign-in:", error);
  }
};



