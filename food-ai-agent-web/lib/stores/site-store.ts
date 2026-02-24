import { create } from "zustand";

interface Site {
  id: string;
  name: string;
  type: string;
  capacity: number;
}

interface SiteStore {
  sites: Site[];
  currentSite: Site | null;
  setSites: (sites: Site[]) => void;
  setCurrentSite: (site: Site) => void;
}

export const useSiteStore = create<SiteStore>((set) => ({
  sites: [],
  currentSite: null,
  setSites: (sites) => set({ sites }),
  setCurrentSite: (site) => set({ currentSite: site }),
}));
