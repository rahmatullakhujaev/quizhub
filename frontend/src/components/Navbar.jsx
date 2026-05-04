import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <nav className="flex items-center justify-between px-8 py-4 bg-slate-900 border-b border-slate-800">
      <Link
        to="/dashboard"
        className="text-xl font-bold bg-gradient-to-r from-violet-500 to-cyan-400 bg-clip-text text-transparent"
      >
        QuizHub
      </Link>

      <div className="flex items-center gap-6">
        <Link
          to="/dashboard"
          className="text-slate-400 hover:text-white text-sm transition"
        >
          Dashboard
        </Link>
        <Link
          to="/questions"
          className="text-slate-400 hover:text-white text-sm transition"
        >
          Questions
        </Link>
        <Link
          to="/collections"
          className="text-slate-400 hover:text-white text-sm transition"
        >
          Collections
        </Link>

        <div className="flex items-center gap-3 ml-4 pl-4 border-l border-slate-700">
          <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-white text-sm font-bold">
            {user?.username?.[0]?.toUpperCase() || "?"}
          </div>
          <span className="text-slate-300 text-sm">{user?.username}</span>
          <button
            onClick={handleLogout}
            className="text-slate-500 hover:text-red-400 text-sm transition"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
