import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Navbar from "../components/Navbar";
import api from "../api/axios";

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [questions, setQuestions] = useState([]);
  const [collections, setCollections] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        const [qRes, cRes, rRes, hRes] = await Promise.all([
          api.get("/questions/"),
          api.get("/collections/"),
          api.get("/rooms/"),
          api.get("/history/"),
        ]);
        if (!cancelled) {
          setQuestions(qRes.data);
          setCollections(cRes.data);
          setRooms(rRes.data);
          setHistory(hRes.data);
        }
      } catch (err) {
        console.error("Failed to fetch dashboard data", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleCreateRoom = async (collectionId) => {
    try {
      const res = await api.post("/rooms/", {
        collection_id: collectionId,
        save_as_collection: false,
      });
      navigate(`/host/${res.data.id}`);
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to create room");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900">
        <Navbar />
        <div className="flex items-center justify-center h-[80vh] text-slate-400">
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <Navbar />

      <div className="max-w-6xl mx-auto px-8 py-8">
        {/* Welcome */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-1">
            Welcome back, {user?.username}
          </h1>
          <p className="text-slate-400">Manage your quizzes and host games</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          <StatCard label="Questions" value={questions.length} emoji="📝" />
          <StatCard label="Collections" value={collections.length} emoji="📚" />
          <StatCard label="Rooms" value={rooms.length} emoji="🎮" />
          <StatCard label="Games Played" value={history.length} emoji="🏆" />
        </div>

        {/* Quick Actions */}
        <div className="flex flex-wrap gap-3 mb-10">
          <Link
            to="/questions"
            className="px-5 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-sm font-medium transition"
          >
            + New Question
          </Link>
          <Link
            to="/collections"
            className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg text-sm font-medium transition"
          >
            + New Collection
          </Link>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Collections — Quick Launch */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">
              Your Collections
            </h2>
            {collections.length === 0 ? (
              <EmptyState
                text="No collections yet"
                link="/collections"
                linkText="Create one"
              />
            ) : (
              <div className="space-y-3">
                {collections.map((c) => (
                  <div
                    key={c.id}
                    className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex items-center justify-between"
                  >
                    <div>
                      <h3 className="text-white font-medium">{c.title}</h3>
                      <p className="text-slate-400 text-sm">
                        {c.question_count} questions
                      </p>
                    </div>
                    <button
                      onClick={() => handleCreateRoom(c.id)}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition"
                    >
                      Host Game
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Rooms */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">
              Recent Rooms
            </h2>
            {rooms.length === 0 ? (
              <EmptyState text="No rooms yet" />
            ) : (
              <div className="space-y-3">
                {rooms.slice(0, 5).map((r) => (
                  <div
                    key={r.id}
                    className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-white font-mono font-bold">
                          {r.room_code}
                        </span>
                        <StatusBadge status={r.status} />
                      </div>
                      <p className="text-slate-400 text-sm mt-1">
                        {new Date(r.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    {r.status === "waiting" && (
                      <Link
                        to={`/host/${r.id}`}
                        className="px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-sm font-medium transition"
                      >
                        Open
                      </Link>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Game History */}
          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold text-white mb-4">
              Game History
            </h2>
            {history.length === 0 ? (
              <EmptyState text="No games played yet" />
            ) : (
              <div className="space-y-3">
                {history.slice(0, 5).map((h) => (
                  <div
                    key={h.id}
                    className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex items-center justify-between"
                  >
                    <div>
                      <p className="text-white font-medium">
                        {h.total_questions} questions · {h.player_count} players
                      </p>
                      <p className="text-slate-400 text-sm">
                        {new Date(h.played_at).toLocaleString()}
                      </p>
                    </div>
                    <Link
                      to={`/results/${h.room_id}`}
                      className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium transition"
                    >
                      View Results
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, emoji }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
      <div className="text-2xl mb-2">{emoji}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-slate-400 text-sm">{label}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = {
    waiting: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    active: "bg-green-500/10 text-green-400 border-green-500/20",
    finished: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  };

  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-mono border ${
        colors[status] || colors.waiting
      }`}
    >
      {status}
    </span>
  );
}

function EmptyState({ text, link, linkText }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-8 text-center">
      <p className="text-slate-500 mb-2">{text}</p>
      {link && (
        <Link
          to={link}
          className="text-violet-400 hover:text-violet-300 text-sm transition"
        >
          {linkText}
        </Link>
      )}
    </div>
  );
}
