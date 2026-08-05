import { ImagesPageContent } from './components/images-page-content';

export default async function ImagesPage() {
  const isAuthenticated = true;

  return <ImagesPageContent isAuthenticated={isAuthenticated} />;
}
