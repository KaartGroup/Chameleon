import logo from './logo.svg';
import './App.css';
import {
  BrowserRouter as Router,
  Switch,
  Route,
  Redirect,
} from "react-router-dom";

import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { PageNotFound } from "./components/PageNotFound";
import { Chameleon } from './components/Chameleon';

function App() {
  return (
      <Router>
        <Header />
        <Switch>
            <Route exact={true} path="/">
              <Redirect to="/chameleon" />
            </Route>
            <Route path="/chameleon">
              <Chameleon />
            </Route>
            <Route component={PageNotFound} />
          </Switch>
        <Footer />
      </Router>
  );
}

export default App;
