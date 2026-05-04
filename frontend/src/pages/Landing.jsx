import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Landing() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      {/* Navbar */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-slate-800">
        <Link
          to="/"
          className="text-2xl font-bold bg-gradient-to-r from-violet-500 to-cyan-400 bg-clip-text text-transparent"
        >
          QuizHub
        </Link>
        <div className="flex gap-3">
          {user ? (
            <Link
              to="/dashboard"
              className="px-5 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-sm font-medium transition"
            >
              Dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className="px-5 py-2.5 text-slate-300 hover:text-white text-sm font-medium transition"
              >
                Log in
              </Link>
              <Link
                to="/register"
                className="px-5 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-sm font-medium transition"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 text-center">
        <div className="mb-6 text-5xl">🧠</div>
        <h1 className="text-5xl md:text-6xl font-bold text-white mb-6 leading-tight">
          Live quizzes,
          <br />
          <span className="bg-gradient-to-r from-violet-500 to-cyan-400 bg-clip-text text-transparent">
            real-time fun
          </span>
        </h1>
        <p className="text-slate-400 text-lg md:text-xl max-w-xl mb-10">
          Create questions, host a room, and challenge your friends — all in
          real time. No signup needed to play.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mb-16">
          <Link
            to="/register"
            className="px-8 py-3.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl text-base font-semibold transition shadow-lg shadow-violet-600/20"
          >
            Create a Quiz
          </Link>
          <JoinForm />
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl w-full mt-4">
          <FeatureCard
            emoji="⚡"
            title="Real-time"
            desc="WebSocket-powered live gameplay"
          />
          <FeatureCard
            emoji="🏆"
            title="Leaderboards"
            desc="Instant scoring and rankings"
          />
          <FeatureCard
            emoji="📱"
            title="No app needed"
            desc="Play from any browser"
          />
        </div>
      </div>

      {/* Footer */}
      <footer className="text-center py-6 text-slate-600 text-sm border-t border-slate-800">
        QuizHub — Database Application and Design Project 2026
      </footer>
    </div>
  );
}

function JoinForm() {
  const handleJoin = (e) => {
    e.preventDefault();
    const code = e.target.code.value.trim().toUpperCase();
    if (code) window.location.href = `/join/${code}`;
  };

  return (
    <form onSubmit={handleJoin} className="flex">
      <input
        name="code"
        placeholder="Room code"
        maxLength={6}
        className="w-32 px-4 py-3.5 bg-slate-800 border border-slate-700 rounded-l-xl text-white text-center text-base font-mono uppercase tracking-widest placeholder:text-slate-500 outline-none focus:border-violet-500 transition"
      />
      <button
        type="submit"
        className="px-6 py-3.5 bg-cyan-500 hover:bg-cyan-600 text-white rounded-r-xl text-base font-semibold transition"
      >
        Join
      </button>
    </form>
  );
}

function FeatureCard({ emoji, title, desc }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 text-center">
      <div className="text-3xl mb-3">{emoji}</div>
      <h3 className="text-white font-semibold mb-1">{title}</h3>
      <p className="text-slate-400 text-sm">{desc}</p>
    </div>
  );
}
