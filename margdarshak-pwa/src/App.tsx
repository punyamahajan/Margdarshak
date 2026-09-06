import { lazy, Suspense, useEffect, useState } from "react";
import { AuthProvider } from "./context/AuthContext";
import { AuthModal } from "./components/AuthModal";
import { StudentProfileModal } from "./components/StudentProfileModal";
import { Home } from "./screens/Home";
import { PlacementDetails } from "./screens/PlacementDetails";
import { studentPlacements } from "./data/studentData";

const CallScreen = lazy(() =>
  import("./screens/CallScreen").then((module) => ({ default: module.CallScreen }))
);
const MatchmakerRequest = lazy(() =>
  import("./screens/MatchmakerRequest").then((module) => ({ default: module.MatchmakerRequest }))
);
const MatchmakerChat = lazy(() =>
  import("./screens/MatchmakerChat").then((module) => ({ default: module.MatchmakerChat }))
);
const AdminWorkspace = lazy(() => import("./screens/AdminWorkspaceComplete").then((module) => ({ default: module.AdminWorkspaceComplete })));

function routeFromLocation(): string {
  return window.location.pathname;
}

function MainRoutes() {
  const [route, setRoute] = useState(routeFromLocation);

  useEffect(() => {
    const handlePopState = () => setRoute(routeFromLocation());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function navigate(path: string) {
    window.history.pushState({}, "", path);
    setRoute(path);
  }

  if (route === "/call") {
    return (
      <Suspense fallback={<main className="route-loading">Preparing your call…</main>}>
        <CallScreen onBack={() => navigate("/")} />
      </Suspense>
    );
  }

  if (route === "/matchmaker") {
    return (
      <Suspense fallback={<main className="route-loading">Opening matchmaker…</main>}>
        <MatchmakerRequest
          onBack={() => navigate("/")}
          onMatched={(bridgeId) => navigate(`/matchmaker/${bridgeId}`)}
        />
      </Suspense>
    );
  }

  if (route === "/admin") {
    return <Suspense fallback={<main className="route-loading">Opening coordinator workspace…</main>}><AdminWorkspace onExit={() => navigate("/")} /></Suspense>;
  }

  const bridgeMatch = route.match(/^\/matchmaker\/([^/]+)$/);
  if (bridgeMatch) {
    return (
      <Suspense fallback={<main className="route-loading">Opening anonymous bridge…</main>}>
        <MatchmakerChat
          bridgeId={decodeURIComponent(bridgeMatch[1])}
          onBack={() => navigate("/matchmaker")}
        />
      </Suspense>
    );
  }

  const placementMatch = route.match(/^\/placements\/([^/]+)$/);
  if (placementMatch) {
    const placement = studentPlacements.find((item) => item.id === decodeURIComponent(placementMatch[1]));
    if (placement) {
      return <PlacementDetails placement={placement} onBack={() => navigate("/")} onAsk={() => navigate("/call")} />;
    }
  }

  return (
    <Home
      onStartCall={() => navigate("/call")}
      onFindMatch={() => navigate("/matchmaker")}
      onOpenPlacement={(id) => navigate(`/placements/${id}`)}
    />
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainRoutes />
      <AuthModal />
      <StudentProfileModal />
    </AuthProvider>
  );
}
