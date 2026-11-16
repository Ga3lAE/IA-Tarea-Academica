import { Landing } from "./pages/Landing";
import { Survey } from "./pages/Survey";
import { usePath } from "./lib/router";

export default function App() {
  const [path, navigate] = usePath();
  if (path.startsWith("/encuesta")) return <Survey onHome={() => navigate("/")} />;
  return <Landing onStart={() => navigate("/encuesta")} />;
}
