import { DocumentNewPage } from "@/components/document/DocumentNewPage";
import { paymentsModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentNewPage config={paymentsModule} />;
}
